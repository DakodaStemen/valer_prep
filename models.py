"""SQLAlchemy database models for patient authorization data."""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class PatientAuth(Base):
    """Patient authorization record model."""

    __tablename__ = "patient_auth"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    auth_number: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )

    __table_args__ = (
        Index("idx_auth_number", "auth_number"),
    )

    def __repr__(self) -> str:
        """String representation of PatientAuth instance."""
        return (
            f"<PatientAuth(id={self.id}, patient_name='{self.patient_name}', "
            f"auth_number='{self.auth_number}', status='{self.status}')>"
        )

