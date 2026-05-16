import random
import string
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import User

password_hash = PasswordHash.recommended()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/users/login")


def hash_password(password: str) -> str:
    """
    Hashes a plaintext password using the recommended hashing algorithm.
    """
    return password_hash.hash(password)


def verify_password(
    plain_password: str, hashed_password: str
) -> bool:
    """
    Verifies a plaintext password against a hashed password.
    """
    return password_hash.verify(plain_password, hashed_password)


def generate_otp(length: int = 6) -> str:
    """Generate a random numeric OTP code."""
    return "".join(random.choices(string.digits, k=length))


def is_otp_expired(
    created_at: datetime, expire_minutes: int = 10
) -> bool:
    """Return True if the OTP is older than expire_minutes."""
    now = datetime.now(UTC)
    return now > created_at + timedelta(minutes=expire_minutes)


def create_access_token(
    data: dict, expires_delta: timedelta | None = None
) -> str:
    """
    Creates a JWT access token with the given data and expiration time.
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key.get_secret_value(),
        algorithm=settings.algorithm,
    )
    return encoded_jwt


def verify_access_token(token: str) -> dict | None:
    """
    Verifies a JWT access token and returns the subject (user id) if valid.
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.algorithm],
            options={
                "require": ["exp", "sub"]
            },  # Ensure 'exp' and 'sub' claims are present
        )
    except jwt.InvalidTokenError:
        return None
    else:
        return payload.get("sub")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Get the currenlty authenticated user"""
    user_id = verify_access_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invaild or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate user_id is a valid UUID
    try:
        uuid_obj = uuid.UUID(user_id, version=4)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.id == uuid_obj))

    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
