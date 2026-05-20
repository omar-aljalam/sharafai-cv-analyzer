import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# AI Schema
class SectionError(BaseModel):
    text: str
    severity: Literal["critical", "warning", "suggestion"]


class SectionResult(BaseModel):
    name: str
    score: float = Field(ge=0, le=100)
    errors: list[SectionError] = []
    suggestions: list[str] = []


class CorrectionPair(BaseModel):
    original: str
    suggested: str
    section: str


class AIAnalysisResult(BaseModel):
    overall_score: float = Field(ge=0, le=100)
    sections: list[SectionResult]
    errors: list[SectionError]
    suggestions: list[CorrectionPair]


# API Schema
class AnalysisResponse(BaseModel):
    id: uuid.UUID
    overall_score: float
    sections: list[SectionResult]
    errors: list[SectionError]
    suggestions: list[CorrectionPair]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnalysisHistoryItem(BaseModel):
    id: uuid.UUID
    overall_score: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnalysisHistoryResponse(BaseModel):
    items: list[AnalysisHistoryItem]
    total: int
