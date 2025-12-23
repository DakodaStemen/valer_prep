"""Database connection and session management."""

import os
from typing import Generator, Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from models import Base, PatientAuth

load_dotenv()


def get_database_url() -> str:
    """Construct database URL from environment variables."""
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "postgres")
    db_name = os.getenv("DB_NAME", "valer_db")
    db_host = os.getenv("DB_HOST", "postgres")
    db_port = os.getenv("DB_PORT", "5432")

    database_url = os.getenv(
        "DATABASE_URL",
        f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}",
    )
    return database_url


def create_engine_instance() -> create_engine:
    """Create and return SQLAlchemy engine instance."""
    database_url = get_database_url()
    return create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False,
    )


engine = create_engine_instance()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Initialize database tables."""
    try:
        Base.metadata.create_all(bind=engine)
    except SQLAlchemyError as e:
        raise RuntimeError(f"Failed to initialize database: {e}") from e


def get_db_session() -> Generator[Session, None, None]:
    """Get database session with proper lifecycle management."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def upsert_patient_auth(
    session: Session,
    patient_name: str,
    auth_number: str,
    status: Optional[str] = None,
) -> PatientAuth:
    """Upsert a patient authorization record.

    Args:
        session: SQLAlchemy session
        patient_name: Name of the patient
        auth_number: Authorization number (unique identifier)
        status: Authorization status (defaults to 'Pending' if not provided)

    Returns:
        PatientAuth instance (created or updated)

    Raises:
        SQLAlchemyError: If database operation fails
    """
    if status is None:
        status = "Pending"

    existing_record = session.query(PatientAuth).filter_by(auth_number=auth_number).first()

    if existing_record:
        existing_record.patient_name = patient_name
        existing_record.status = status
        return existing_record

    new_record = PatientAuth(
        patient_name=patient_name,
        auth_number=auth_number,
        status=status,
    )
    session.add(new_record)
    return new_record


def check_db_connection() -> bool:
    """Check if database connection is healthy.

    Returns:
        True if connection is healthy, False otherwise
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False

