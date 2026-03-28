"""Dataset HTTP routes."""

from fastapi import APIRouter, Depends, status

from api.dependencies import get_dataset_repository
from repositories.dataset_repository import DatasetRepository
from schemas.datasets import DatasetCreateRequest, DatasetResponse
from services.health_score import calculate_health_score

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post(
    "/",
    response_model=DatasetResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_dataset(
    body: DatasetCreateRequest,
    repo: DatasetRepository = Depends(get_dataset_repository),
) -> DatasetResponse:
    """Register a new dataset and persist a computed health score."""
    metadata_for_score = {
        "description": body.metadata.description,
        "language": body.metadata.language or body.language,
        "tags": body.metadata.tags,
    }
    health_score = calculate_health_score(metadata_for_score)
    row = repo.create(
        name=body.name,
        language=body.language,
        dataset_type=body.dataset_type,
        file_url=str(body.file_url),
        health_score=health_score,
    )
    return DatasetResponse.model_validate(row)
