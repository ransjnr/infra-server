"""FastAPI dependency providers."""

from fastapi import Depends
from sqlalchemy.orm import Session

from database import get_db
from repositories.dataset_repository import DatasetRepository


def get_dataset_repository(session: Session = Depends(get_db)) -> DatasetRepository:
    return DatasetRepository(session)
