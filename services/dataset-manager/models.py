"""SQLAlchemy ORM models."""

import uuid

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    pass


class Dataset(Base):
    """Registered dataset row."""

    __tablename__ = "datasets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    language: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dataset_type: Mapped[str] = mapped_column("type", String(128), nullable=False)
    file_url: Mapped[str] = mapped_column(Text, nullable=False)
    health_score: Mapped[int] = mapped_column(Integer, nullable=False)
