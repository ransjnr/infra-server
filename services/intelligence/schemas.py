"""Pydantic models for /analyze."""

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    """Input payload for text analysis."""

    text: str = Field(..., min_length=1, max_length=16_000)
    language_pair: str | None = Field(
        default=None,
        description="Optional Khaya pair (e.g. tw-en). If omitted, inferred from code-switch scan.",
    )


class AnalyzeResponse(BaseModel):
    """Unified analysis result."""

    detected_languages: list[str]
    translation: str
    sentiment_score: float = Field(
        ...,
        description="Approximate polarity in [-1, 1] from the multilingual sentiment model.",
    )
    modality: str = Field(
        ...,
        description="code-switched | english | twi | unknown (heuristic).",
    )
