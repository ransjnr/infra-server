"""Pydantic models for dataset API requests and responses."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class DatasetMetadataRequest(BaseModel):
    """Metadata used for health scoring."""

    description: str = ""
    language: str | None = Field(
        default=None,
        description="Optional override for NLP language check; defaults to dataset language.",
    )
    tags: list[str] = Field(default_factory=list)


class DatasetCreateRequest(BaseModel):
    """Register a new dataset."""

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=512)
    language: str = Field(..., min_length=1, max_length=64)
    dataset_type: str = Field(..., min_length=1, max_length=128, alias="type")
    file_url: HttpUrl
    metadata: DatasetMetadataRequest = Field(default_factory=DatasetMetadataRequest)


class DatasetResponse(BaseModel):
    """Persisted dataset row."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    language: str
    dataset_type: str = Field(serialization_alias="type")
    file_url: str
    health_score: int
