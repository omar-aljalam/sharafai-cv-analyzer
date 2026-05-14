from fastapi import FastAPI

app = FastAPI(
    title="SharafAI CV Analyzer API",
    description="API for analyzing CVs using SharafAI",
    version="1.0",
)


@app.get("/")
async def read_root():
    return {"message": "Welcome to the SharafAI CV Analyzer API!"}
