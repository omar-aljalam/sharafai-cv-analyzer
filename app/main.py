from typing import Annotated

from analysis.router import router as analysis_router
from auth.router import router as auth_router
from fastapi import Depends, FastAPI, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Analysis, PasswordResetOTP, User  # noqa F401

app = FastAPI(
    title="SharafAI CV Analyzer API",
    description="API for analyzing CVs using SharafAI",
    version="1.0",
)

app.include_router(auth_router)
app.include_router(analysis_router)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    response.headers["X-Frame-Options"] = "SAMEORIGIN"

    response.headers["X-Content-Type-Options"] = "nosniff"

    if "Referrer-Policy" not in response.headers:
        response.headers["Referrer-Policy"] = (
            "strict-origin-when-cross-origin"
        )

    if request.url.hostname not in ("localhost", "127.0.0.1"):
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains"
        )

    return response


@app.get("/")
async def read_root():
    return {"message": "Welcome to the SharafAI CV Analyzer API!"}


@app.get(
    "/health",
    tags=["General"],
    summary="Health check",
    description="Returns the health status of the API and its dependencies.",
    responses={
        200: {"description": "All systems operational"},
        503: {
            "description": "One or more dependencies are unavailable"
        },
    },
)
async def health_check(db: Annotated[AsyncSession, Depends(get_db)]):
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from exc

    return {
        "status": "healthy",
        "dependencies": {
            "database": "ok",
        },
    }
