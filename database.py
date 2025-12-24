"""Database connection and session management."""

import os
from contextlib import contextmanager
from typing import Generator, Optional
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import create_engine, text, desc
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from models import Base, PatientAuth, ScrapeRun

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


def create_engine_instance() -> Engine:
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


@contextmanager
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
    session.flush()
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


def create_scrape_run(session: Session) -> ScrapeRun:
    """Create a new scrape run record.

    Args:
        session: SQLAlchemy session

    Returns:
        ScrapeRun instance with started_at timestamp
    """
    scrape_run = ScrapeRun(
        started_at=datetime.utcnow(),
        status="running",
        records_found=0,
        records_saved=0,
    )
    session.add(scrape_run)
    session.flush()
    return scrape_run


def update_scrape_run(
    session: Session,
    scrape_run_id: int,
    records_found: int,
    records_saved: int,
    status: str = "success",
    error_message: Optional[str] = None,
) -> ScrapeRun:
    """Update a scrape run with completion data and metrics.

    Args:
        session: SQLAlchemy session
        scrape_run_id: ID of the scrape run to update
        records_found: Number of records found during scrape
        records_saved: Number of records successfully saved
        status: Final status ('success' or 'failed')
        error_message: Error message if status is 'failed'

    Returns:
        Updated ScrapeRun instance

    Raises:
        ValueError: If scrape_run_id not found
    """
    scrape_run = session.query(ScrapeRun).filter_by(id=scrape_run_id).first()
    if not scrape_run:
        raise ValueError(f"ScrapeRun with id {scrape_run_id} not found")

    scrape_run.completed_at = datetime.utcnow()
    scrape_run.records_found = records_found
    scrape_run.records_saved = records_saved
    scrape_run.status = status
    scrape_run.error_message = error_message

    if scrape_run.started_at and scrape_run.completed_at:
        delta = scrape_run.completed_at - scrape_run.started_at
        scrape_run.duration_seconds = delta.total_seconds()

    session.flush()
    return scrape_run


def get_latest_scrape_run(session: Session) -> Optional[ScrapeRun]:
    """Get the most recent scrape run.

    Args:
        session: SQLAlchemy session

    Returns:
        Most recent ScrapeRun instance, or None if no runs exist
    """
    return session.query(ScrapeRun).order_by(desc(ScrapeRun.started_at)).first()


def get_total_records_count(session: Session) -> int:
    """Get total count of patient authorization records.

    Args:
        session: SQLAlchemy session

    Returns:
        Total number of records in patient_auth table
    """
    return session.query(PatientAuth).count()

