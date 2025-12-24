"""Flask REST API for Valer-Sync Pro dashboard."""

import os
import logging
import threading
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from dotenv import load_dotenv
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

from database import (
    get_db_session,
    init_db,
    check_db_connection,
    upsert_patient_auth,
    create_scrape_run,
    update_scrape_run,
    get_latest_scrape_run,
    get_total_records_count,
)
from models import PatientAuth, ScrapeRun
from scraper import PortalScraper

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Thread-safe job status storage
job_status: Dict[str, Dict[str, Any]] = {}
job_lock = threading.Lock()


def run_scrape_job(job_id: str, username: str, password: str, headless: bool = True) -> None:
    """Execute scrape job in background thread.

    Args:
        job_id: Unique job identifier
        username: Portal username
        password: Portal password
        headless: Run browser in headless mode
    """
    scrape_run_id: Optional[int] = None

    try:
        with job_lock:
            job_status[job_id] = {
                "status": "running",
                "progress": "Initializing scraper...",
                "started_at": datetime.utcnow().isoformat(),
            }

        with get_db_session() as session:
            scrape_run = create_scrape_run(session)
            scrape_run_id = scrape_run.id
            session.commit()

        scraper = PortalScraper(headless=headless)

        def progress_callback(message: str) -> None:
            with job_lock:
                if job_id in job_status:
                    job_status[job_id]["progress"] = message

        authorizations = scraper.run_full_extraction(
            username=username,
            password=password,
            progress_callback=progress_callback,
        )

        records_saved = 0
        with get_db_session() as session:
            for auth_data in authorizations:
                try:
                    upsert_patient_auth(
                        session=session,
                        patient_name=auth_data["patient_name"],
                        auth_number=auth_data["auth_number"],
                        status=auth_data.get("status", "Pending"),
                    )
                    records_saved += 1
                except Exception as e:
                    logger.error(f"Failed to persist authorization {auth_data.get('auth_number')}: {e}")

            if scrape_run_id:
                update_scrape_run(
                    session=session,
                    scrape_run_id=scrape_run_id,
                    records_found=len(authorizations),
                    records_saved=records_saved,
                    status="success",
                )
            session.commit()

        with job_lock:
            job_status[job_id] = {
                "status": "completed",
                "progress": f"Successfully saved {records_saved} records",
                "started_at": job_status.get(job_id, {}).get("started_at"),
                "completed_at": datetime.utcnow().isoformat(),
                "records_found": len(authorizations),
                "records_saved": records_saved,
            }

    except Exception as e:
        logger.error(f"Scrape job {job_id} failed: {e}", exc_info=True)
        error_message = str(e)

        with get_db_session() as session:
            if scrape_run_id:
                update_scrape_run(
                    session=session,
                    scrape_run_id=scrape_run_id,
                    records_found=0,
                    records_saved=0,
                    status="failed",
                    error_message=error_message,
                )
            session.commit()

        with job_lock:
            job_status[job_id] = {
                "status": "failed",
                "progress": f"Error: {error_message}",
                "started_at": job_status.get(job_id, {}).get("started_at"),
                "completed_at": datetime.utcnow().isoformat(),
                "error": error_message,
            }


@app.route("/")
def index() -> str:
    """Serve the SPA frontend."""
    return render_template("index.html")


@app.route("/health")
def health() -> Dict[str, Any]:
    """Health check endpoint with engine status and metrics."""
    db_healthy = check_db_connection()

    last_sync_time: Optional[str] = None
    try:
        with get_db_session() as session:
            latest_run = get_latest_scrape_run(session)
            if latest_run and latest_run.completed_at:
                last_sync_time = latest_run.completed_at.isoformat()
    except Exception as e:
        logger.warning(f"Error fetching last sync time: {e}")

    return jsonify({
        "status": "healthy" if db_healthy else "degraded",
        "database": "connected" if db_healthy else "disconnected",
        "last_sync_time": last_sync_time,
        "timestamp": datetime.utcnow().isoformat(),
    })


@app.route("/api/authorizations")
def get_authorizations() -> Dict[str, Any]:
    """Get all patient authorization records."""
    try:
        with get_db_session() as session:
            records = session.query(PatientAuth).order_by(PatientAuth.created_at.desc()).all()
            return jsonify({
                "success": True,
                "count": len(records),
                "data": [record.to_dict() for record in records],
            })
    except Exception as e:
        logger.error(f"Error fetching authorizations: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/scrape", methods=["POST"])
def trigger_scrape() -> Dict[str, Any]:
    """Trigger asynchronous scraping job."""
    username = os.getenv("PORTAL_USERNAME", "tomsmith")
    password = os.getenv("PORTAL_PASSWORD", "SuperSecretPassword!")
    headless = os.getenv("SELENIUM_HEADLESS", "true").lower() == "true"

    job_id = str(uuid.uuid4())

    thread = threading.Thread(
        target=run_scrape_job,
        args=(job_id, username, password, headless),
        daemon=True,
    )
    thread.start()

    return jsonify({
        "success": True,
        "job_id": job_id,
        "message": "Scrape job started",
    })


@app.route("/api/scrape/status/<job_id>")
def get_scrape_status(job_id: str) -> Dict[str, Any]:
    """Get status of a scrape job."""
    with job_lock:
        job_data = job_status.get(job_id)

    if not job_data:
        return jsonify({
            "success": False,
            "error": "Job not found",
        }), 404

    return jsonify({
        "success": True,
        "job_id": job_id,
        **job_data,
    })


@app.route("/api/authorizations/<int:auth_id>", methods=["PATCH"])
def update_authorization(auth_id: int) -> Dict[str, Any]:
    """Update a patient authorization record."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        with get_db_session() as session:
            record = session.query(PatientAuth).filter_by(id=auth_id).first()
            if not record:
                return jsonify({"success": False, "error": "Record not found"}), 404

            if "patient_name" in data:
                record.patient_name = data["patient_name"]
            if "auth_number" in data:
                record.auth_number = data["auth_number"]
            if "status" in data:
                record.status = data["status"]

            record.is_manually_edited = True
            record.updated_at = datetime.utcnow()

            session.commit()

            return jsonify({
                "success": True,
                "data": record.to_dict(),
            })
    except Exception as e:
        logger.error(f"Error updating authorization {auth_id}: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/stats")
def get_stats() -> Dict[str, Any]:
    """Get dashboard statistics."""
    try:
        with get_db_session() as session:
            total_records = get_total_records_count(session)
            latest_run = get_latest_scrape_run(session)

            stats = {
                "total_records": total_records,
                "last_sync_time": None,
                "last_sync_status": None,
                "last_sync_duration": None,
                "last_sync_records_saved": None,
            }

            if latest_run:
                stats["last_sync_time"] = latest_run.completed_at.isoformat() if latest_run.completed_at else None
                stats["last_sync_status"] = latest_run.status
                stats["last_sync_duration"] = latest_run.duration_seconds
                stats["last_sync_records_saved"] = latest_run.records_saved

            return jsonify({
                "success": True,
                "data": stats,
            })
    except Exception as e:
        logger.error(f"Error fetching stats: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


def wait_for_database(max_retries: int = 30, retry_delay: int = 2) -> bool:
    """Wait for database to become available.

    Args:
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds

    Returns:
        True if database is available, False otherwise
    """
    logger.info("Waiting for database connection...")
    for attempt in range(max_retries):
        if check_db_connection():
            logger.info("Database connection established")
            return True
        logger.info(f"Database not ready, retrying... ({attempt + 1}/{max_retries})")
        time.sleep(retry_delay)

    logger.error("Database connection failed after maximum retries")
    return False


if __name__ == "__main__":
    if not wait_for_database():
        logger.error("Failed to establish database connection")
        exit(1)

    logger.info("Initializing database schema...")
    init_db()
    logger.info("Database schema initialized")

    port = int(os.getenv("FLASK_PORT", "5000"))
    debug = os.getenv("FLASK_ENV", "production").lower() == "development"

    logger.info(f"Starting Flask server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=debug)

