import httpx

from app.config import settings
from app.analysis.schemas import AIAnalysisResult


async def call_ai_analysis(cv_text: str) -> AIAnalysisResult:
    """
    Send extracted CV text to the AI team's analysis endpoint and return
    the validated result.

    Raises:
      TimeoutError   if the AI service does not respond within 60 seconds
      ValueError     if the response does not match the expected schema
      httpx.HTTPStatusError  if the AI service returns a non-2xx status
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                settings.ai_service_url,
                json={"cv_text": cv_text},
            )
            response.raise_for_status()
        except httpx.TimeoutException:
            raise TimeoutError(
                "The AI analysis service did not respond in time. Please try again."
            )

    try:
        return AIAnalysisResult.model_validate(response.json())
    except Exception as exc:
        raise ValueError(
            f"AI service returned an unexpected response format: {exc}"
        ) from exc
