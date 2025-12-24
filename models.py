"""SQLAlchemy database models for patient authorization data."""

from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import DateTime, Integer, String, Index, Boolean, Float, Text
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
    is_manually_edited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        index=True,
    )

    __table_args__ = (
        Index("idx_auth_number", "auth_number"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize PatientAuth instance to dictionary for JSON responses."""
        return {
            "id": self.id,
            "patient_name": self.patient_name,
            "auth_number": self.auth_number,
            "status": self.status,
            "is_manually_edited": self.is_manually_edited,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        """String representation of PatientAuth instance."""
        return (
            f"<PatientAuth(id={self.id}, patient_name='{self.patient_name}', "
            f"auth_number='{self.auth_number}', status='{self.status}', "
            f"is_manually_edited={self.is_manually_edited})>"
        )


class ScrapeRun(Base):
    """Scrape run metrics model for instrumentation tracking."""

    __tablename__ = "scrape_run"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    records_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_saved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="running", index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize ScrapeRun instance to dictionary for JSON responses."""
        return {
            "id": self.id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "records_found": self.records_found,
            "records_saved": self.records_saved,
            "status": self.status,
            "error_message": self.error_message,
        }

    def __repr__(self) -> str:
        """String representation of ScrapeRun instance."""
        return (
            f"<ScrapeRun(id={self.id}, status='{self.status}', "
            f"records_saved={self.records_saved}, duration_seconds={self.duration_seconds})>"
        )

