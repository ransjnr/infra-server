"""Dataset persistence (repository pattern)."""

from sqlalchemy.orm import Session

from models import Dataset


class DatasetRepository:
    """Encapsulates all SQLAlchemy access for the datasets table."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        name: str,
        language: str,
        dataset_type: str,
        file_url: str,
        health_score: int,
    ) -> Dataset:
        row = Dataset(
            name=name,
            language=language,
            dataset_type=dataset_type,
            file_url=file_url,
            health_score=health_score,
        )
        self._session.add(row)
        try:
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        self._session.refresh(row)
        return row
