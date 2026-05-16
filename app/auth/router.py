from datetime import UTC, datetime, timedelta
from typing import Annotated

from auth.schemas import (
    ChangePasswordRequest,
    CreateUser,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    Token,
    UserResponse,
)
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import delete as sql_delete
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.email_service import send_password_reset_otp_email
from app.auth.services import (
    CurrentUser,
    create_access_token,
    generate_otp,
    hash_password,
    verify_password,
)
from app.config import settings
from app.database import get_db
from app.models import PasswordResetOTP, User

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    user: CreateUser, db: Annotated[AsyncSession, Depends(get_db)]
):
    # check if email already exists
    result = await db.execute(
        select(User).where(
            func.lower(User.email) == user.email.lower()
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    new_user = User(
        name=user.name,
        email=user.email.lower(),
        password_hash=hash_password(user.password),
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Look up user by email (username field in OAuth2PasswordRequestForm)
    result = await db.execute(
        select(User).where(
            func.lower(User.email) == form_data.username.lower()
        ),
    )

    user = result.scalars().first()

    # Verify user exists and password is correct
    if not user or not verify_password(
        form_data.password, user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(
        minutes=settings.access_token_expire_minutes
    )
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserResponse)
async def get_current_user(current_user: CurrentUser):
    return current_user


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    requested_data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(User).where(
            func.lower(User.email) == requested_data.email.lower(),
        ),
    )
    user = result.scalars().first()

    if user:
        await db.execute(
            sql_delete(PasswordResetOTP).where(
                PasswordResetOTP.user_id == user.id,
            ),
        )

        otp = generate_otp()
        expires_at = datetime.now(UTC) + timedelta(
            minutes=settings.otp_expire_minutes
        )

        reset_token = PasswordResetOTP(
            user_id=user.id,
            otp=otp,
            expires_at=expires_at,
        )
        db.add(reset_token)
        await db.commit()

        background_tasks.add_task(
            send_password_reset_otp_email,
            to_email=user.email,
            username=user.name,
            otp=otp,
        )

    return {
        "message": "If an account exists with this email, you will receive password reset instructions."
    }


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    request_data: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    otp = request_data.otp

    result = await db.execute(
        select(PasswordResetOTP).where(
            PasswordResetOTP.otp == otp,
        )
    )
    reset_token = result.scalars().first()

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    if reset_token.expires_at < datetime.now(UTC):
        await db.delete(reset_token)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token",
        )

    result = await db.execute(
        select(User).where(User.id == reset_token.user_id),
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token",
        )

    user.password_hash = hash_password(request_data.new_password)

    await db.execute(
        sql_delete(PasswordResetOTP).where(
            PasswordResetOTP.user_id == user.id,
        ),
    )
    await db.commit()
    return {
        "message": "Password reset successfuly. You can now log in with your new password."
    }


@router.patch("/me/password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not verify_password(
        password_data.current_password, current_user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.password_hash = hash_password(
        password_data.new_password
    )

    await db.execute(
        sql_delete(PasswordResetOTP).where(
            PasswordResetOTP.user_id == current_user.id,
        ),
    )
    await db.commit()
    return {"message": "Password changed successfully"}


@router.delete("/me/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await db.delete(current_user)
    await db.commit()
    return None
