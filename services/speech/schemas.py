"""API response models for speech routes."""

from pydantic import BaseModel, Field


class TranscribeResponse(BaseModel):
    """Transcription plus downstream intelligence (translation / analysis)."""

    transcription: str = Field(..., description="Whisper transcript of the uploaded audio.")
    translation: str
    detected_languages: list[str]
    sentiment_score: float
    modality: str
