"""
celery_worker.py — Background task definitions (Refactored to remove Celery).
"""
import sys
import os

_PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_DIR not in sys.path:
    sys.path.insert(0, _PROJECT_DIR)
# Also add the current working directory just in case
cwd = os.getcwd()
if cwd not in sys.path:
    sys.path.insert(0, cwd)

import logging
from datetime import datetime, timezone

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# Instantiate Celery application
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery("financial_analyzer", broker=REDIS_URL, backend=REDIS_URL)

logger = logging.getLogger(__name__)

# ── Helper: run the CrewAI pipeline ──────────────────────────────────────────
def _run_crew(query: str, file_path: str) -> str:
    """
    Execute the CrewAI analysis pipeline.
    Imported here (inside the task) to avoid circular imports at module level.
    """
    from crewai import Crew, Process
    from agents import financial_analyst, verifier, investment_advisor, risk_assessor
    from task import (
        analyze_financial_document,
        verification,
        investment_analysis,
        risk_assessment,
    )

    crew = Crew(
        agents=[verifier, financial_analyst, investment_advisor, risk_assessor],
        tasks=[verification, analyze_financial_document, investment_analysis, risk_assessment],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff(inputs={"query": query, "file_path": file_path})
    return str(result)


# ── Background task ────────────────────────────────────────────────────────
@celery_app.task(name="run_analysis_task")
def run_analysis_task(job_id: str, query: str, file_path: str) -> dict:
    """
    Background task: run the full CrewAI analysis pipeline and persist results.

    Args:
        job_id (str): UUID of the AnalysisJob record to update.
        query  (str): User's analysis query.
        file_path (str): Path to the saved PDF on disk.

    Returns:
        dict: {"job_id": ..., "status": "COMPLETED" | "FAILED"}
    """
    from database import SessionLocal
    from models import AnalysisJob

    db = SessionLocal()
    try:
        # ── Mark job as PROCESSING ──────────────────────────────────────────
        job: AnalysisJob | None = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
        if not job:
            logger.error("Job %s not found in database.", job_id)
            return {"job_id": job_id, "status": "FAILED", "error": "Job record not found"}

        job.status = "PROCESSING"
        job.updated_at = datetime.now(timezone.utc)
        db.commit()

        logger.info("Starting analysis for job %s | query=%r | file=%s", job_id, query, file_path)

        # ── Run the CrewAI pipeline ─────────────────────────────────────────
        result_text = _run_crew(query=query, file_path=file_path)

        # ── Mark job as COMPLETED ───────────────────────────────────────────
        job.status = "COMPLETED"
        job.result = result_text
        job.updated_at = datetime.now(timezone.utc)
        db.commit()

        logger.info("Job %s completed successfully.", job_id)
        return {"job_id": job_id, "status": "COMPLETED"}

    except Exception as exc:
        logger.exception("Job %s failed: %s", job_id, exc)
        # ── Mark job as FAILED ──────────────────────────────────────────────
        if job:
            job.status = "FAILED"
            job.error = str(exc)
            job.updated_at = datetime.now(timezone.utc)
            db.commit()
        return {"job_id": job_id, "status": "FAILED", "error": str(exc)}

    finally:
        # ── Clean up uploaded PDF ───────────────────────────────────────────
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.debug("Cleaned up temp file: %s", file_path)
            except OSError as e:
                logger.warning("Could not delete temp file %s: %s", file_path, e)
        db.close()
