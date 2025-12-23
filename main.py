"""Main entry point for Valer Automation POC."""

import os
import sys
import logging
from typing import List, Dict

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from database import get_db_session, init_db, check_db_connection, upsert_patient_auth
from scraper import PortalScraper

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def wait_for_database(max_retries: int = 30, retry_delay: int = 2) -> bool:
    """Wait for database to become available.

    Args:
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds

    Returns:
        True if database is available, False otherwise
    """
    import time

    logger.info("Waiting for database connection...")
    for attempt in range(max_retries):
        if check_db_connection():
            logger.info("Database connection established")
            return True
        logger.info(f"Database not ready, retrying... ({attempt + 1}/{max_retries})")
        time.sleep(retry_delay)

    logger.error("Database connection failed after maximum retries")
    return False


def persist_authorizations(session: Session, authorizations: List[Dict[str, str]]) -> int:
    """Persist authorization records to database.

    Args:
        session: SQLAlchemy database session
        authorizations: List of authorization dictionaries

    Returns:
        Number of records processed
    """
    processed = 0
    for auth_data in authorizations:
        try:
            upsert_patient_auth(
                session=session,
                patient_name=auth_data["patient_name"],
                auth_number=auth_data["auth_number"],
                status=auth_data.get("status", "Pending"),
            )
            processed += 1
        except Exception as e:
            logger.error(f"Failed to persist authorization {auth_data.get('auth_number')}: {e}")
            continue

    return processed


def main() -> int:
    """Main orchestration function.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        if not wait_for_database():
            logger.error("Failed to establish database connection")
            return 1

        logger.info("Initializing database schema...")
        init_db()
        logger.info("Database schema initialized")

        portal_username = os.getenv("PORTAL_USERNAME", "tomsmith")
        portal_password = os.getenv("PORTAL_PASSWORD", "SuperSecretPassword!")
        headless_mode = os.getenv("SELENIUM_HEADLESS", "true").lower() == "true"

        logger.info("Starting portal scraper...")
        scraper = PortalScraper(headless=headless_mode)

        logger.info("Executing full extraction workflow...")
        authorizations = scraper.run_full_extraction(
            username=portal_username,
            password=portal_password,
        )

        if not authorizations:
            logger.warning("No authorizations extracted")
            return 0

        logger.info(f"Extracted {len(authorizations)} authorization records")

        logger.info("Persisting authorizations to database...")
        session_gen = get_db_session()
        session = next(session_gen)

        try:
            processed = persist_authorizations(session, authorizations)
            logger.info(f"Successfully persisted {processed}/{len(authorizations)} records")
        except Exception as e:
            logger.error(f"Error persisting authorizations: {e}")
            return 1
        finally:
            try:
                next(session_gen, None)
            except StopIteration:
                pass

        logger.info("Automation workflow completed successfully")
        return 0

    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Fatal error in main workflow: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

