from auth.router import router as auth_router
from fastapi import FastAPI

from app.models import User  # noqa F401

app = FastAPI(
    title="SharafAI CV Analyzer API",
    description="API for analyzing CVs using SharafAI",
    version="1.0",
)

app.include_router(auth_router)


@app.get("/")
async def read_root():
    return {"message": "Welcome to the SharafAI CV Analyzer API!"}
