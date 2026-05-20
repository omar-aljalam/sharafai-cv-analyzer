import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.services import CurrentUser
from app.database import get_db
from app.models import Analysis

from .ai_service import call_ai_analysis
from .extraction import extract_text
from .pdf_service import generate_corrected_pdf
from .schemas import (
    AnalysisHistoryItem,
    AnalysisHistoryResponse,
    AnalysisResponse,
    CorrectionPair,
    SectionError,
    SectionResult,
)

router = APIRouter(prefix="/api/analyses", tags=["analyses"])

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/jpg",
    "image/png",
}
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ANALYSIS_LIMIT = 10


@router.post(
    "/upload",
    response_model=AnalysisResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a CV and receive AI analysis",
)
async def upload_and_analyze(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    file: Annotated[
        UploadFile, File(description="CV file — PDF, JPG, or PNG")
    ],
) -> AnalysisResponse:
    # 1. Validate MIME type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type. Please upload a PDF, JPG, or PNG.",
        )

    file_bytes = await file.read()

    # 2. Validate file size
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {MAX_FILE_SIZE_MB} MB limit.",
        )

    # 3. Check per-user analysis limit
    count_result = await db.execute(
        select(func.count(Analysis.id)).where(
            Analysis.user_id == current_user.id
        )
    )
    if count_result.scalar_one() >= ANALYSIS_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"You have reached your limit of {ANALYSIS_LIMIT} analyses.",
        )

    # 4. Extract text — file bytes are never written to disk
    try:
        cv_text = extract_text(file_bytes, file.filename or "cv")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    finally:
        del file_bytes  # Free memory immediately after use

    if not cv_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No text could be extracted from the file. Please check the file is readable.",
        )

    # 5. Send extracted text to the AI team's service
    try:
        ai_result = await call_ai_analysis(cv_text)
    except TimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(exc),
        )
    except (ValueError, Exception):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI analysis service returned an unexpected response. Please try again.",
        )

    # 6. Save result to DB
    analysis = Analysis(
        user_id=current_user.id,
        overall_score=ai_result.overall_score,
        sections=[s.model_dump() for s in ai_result.sections],
        errors=[e.model_dump() for e in ai_result.errors],
        suggestions=[s.model_dump() for s in ai_result.suggestions],
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    return _to_response(analysis)


@router.get(
    "/history",
    response_model=AnalysisHistoryResponse,
    summary="Get the current user's analysis history",
)
async def get_history(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AnalysisHistoryResponse:
    result = await db.execute(
        select(Analysis)
        .where(Analysis.user_id == current_user.id)
        .order_by(Analysis.created_at.desc())
    )
    analyses = result.scalars().all()

    items = [
        AnalysisHistoryItem(
            id=a.id,
            overall_score=a.overall_score,
            created_at=a.created_at,
        )
        for a in analyses
    ]
    return AnalysisHistoryResponse(items=items, total=len(items))


@router.get(
    "/{analysis_id}",
    response_model=AnalysisResponse,
    summary="Get full details of a single past analysis",
)
async def get_analysis(
    analysis_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AnalysisResponse:
    analysis = await _get_owned_analysis(
        analysis_id, current_user.id, db
    )
    return _to_response(analysis)


@router.get(
    "/{analysis_id}/export",
    summary="Download corrected CV as a watermarked PDF",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
async def export_corrected_pdf(
    analysis_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    analysis = await _get_owned_analysis(
        analysis_id, current_user.id, db
    )

    suggestions = [
        CorrectionPair(**s) for s in (analysis.suggestions or [])
    ]

    try:
        pdf_bytes = generate_corrected_pdf(
            suggestions=suggestions,
            candidate_name=current_user.name,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate the PDF. Please try again.",
        )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="sharafai_cv_{analysis_id}.pdf"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )


async def _get_owned_analysis(
    analysis_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> Analysis:
    """Fetch an analysis that belongs to the requesting user, or raise 404."""
    result = await db.execute(
        select(Analysis).where(
            Analysis.id == analysis_id,
            Analysis.user_id == user_id,
        )
    )
    analysis = result.scalars().first()
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found.",
        )
    return analysis


def _to_response(analysis: Analysis) -> AnalysisResponse:
    return AnalysisResponse(
        id=analysis.id,
        overall_score=analysis.overall_score,
        sections=[
            SectionResult(**s) for s in (analysis.sections or [])
        ],
        errors=[SectionError(**e) for e in (analysis.errors or [])],
        suggestions=[
            CorrectionPair(**s) for s in (analysis.suggestions or [])
        ],
        created_at=analysis.created_at,
    )
