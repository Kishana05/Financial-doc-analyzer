"""
main.py — FastAPI application entry point.

Endpoints:
    GET  /                     Health check
    POST /analyze              Submit a financial PDF for analysis (async via Celery)
    GET  /results/{job_id}     Poll the status / fetch results of a job
    GET  /jobs                 List all jobs (paginated)
"""
import os
import uuid
import logging

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from dotenv import load_dotenv

load_dotenv()

# Bug Fix #13: import task object under an alias to avoid name collision with
#              the endpoint function that was previously named identically.
from task import analyze_financial_document as analyze_financial_document_task  # noqa: F401

from database import get_db, init_db
from models import AnalysisJob
from schemas import JobSubmittedResponse, JobResultResponse, JobListResponse
from celery_worker import run_analysis_task

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Financial Document Analyzer",
    description=(
        "AI-powered financial document analysis using a multi-agent CrewAI pipeline. "
        "Upload a PDF and receive structured investment analysis, risk assessment, and document verification."
    ),
    version="2.0.0",
)

# ── CORS (allow browser requests from any origin during local development) ────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files (React frontend) ─────────────────────────────────────────────
_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_STATIC_DIR):
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


@app.on_event("startup")
def on_startup():
    """Initialize database tables on startup."""
    init_db()
    logger.info("Database initialized successfully.")


# ── Frontend (serve React app) ───────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve the React frontend."""
    index_path = os.path.join(_STATIC_DIR, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return {
        "message": "Financial Document Analyzer API is running",
        "version": "2.0.0",
        "status": "healthy",
        "note": "Frontend not found. Place static/index.html to enable the UI.",
    }

# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health", summary="Health Check")
async def root():
    """Health check endpoint — verifies the API is running."""
    return {
        "message": "Financial Document Analyzer API is running",
        "version": "2.0.0",
        "status": "healthy",
    }


# ── Submit analysis job ───────────────────────────────────────────────────────
# Bug Fix #14: renamed from `analyze_financial_document` (was colliding with imported task)
@app.post(
    "/analyze",
    response_model=JobSubmittedResponse,
    status_code=202,
    summary="Submit Financial Document for Analysis",
)
async def analyze_document_endpoint(
    file: UploadFile = File(..., description="PDF financial document to analyze"),
    query: str = Form(
        default="Provide a comprehensive analysis of this financial document.",
        description="Specific question or analysis focus",
    ),
    db: Session = Depends(get_db),
):
    """
    Submit a financial PDF for asynchronous AI-powered analysis.

    - Saves the uploaded file temporarily.
    - Creates a database record with status **PENDING**.
    - Dispatches a Celery background task for processing.
    - Returns a `job_id` immediately — no waiting for the analysis to complete.

    Poll `GET /results/{job_id}` to retrieve the result.
    """
    # Bug Fix #17: was `if query=="" or query is None` — fixed order + cleaner logic
    if not query or not query.strip():
        query = "Provide a comprehensive analysis of this financial document."

    # Validate file type
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        if not (file.filename or "").lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are supported. Please upload a .pdf file.",
            )

    job_id = str(uuid.uuid4())
    file_path = f"data/financial_document_{job_id}.pdf"

    try:
        # Ensure data directory exists
        os.makedirs("data", exist_ok=True)

        # Save uploaded file to disk (Celery worker will read it)
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        with open(file_path, "wb") as f:
            f.write(content)

        # Persist job record in DB
        job = AnalysisJob(
            id=job_id,
            query=query.strip(),
            filename=file.filename,
            status="PENDING",
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        # Dispatch task via Celery
        run_analysis_task.delay(
            job_id=job_id,
            query=query.strip(),
            file_path=file_path,
        )

        logger.info("Job %s queued for file %s", job_id, file.filename)
        return JobSubmittedResponse(
            job_id=job_id,
            status="PENDING",
            message=(
                f"Job submitted successfully. "
                f"Poll GET /results/{job_id} to retrieve your analysis."
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to submit job: %s", e)
        # Clean up file if something went wrong before the task was dispatched
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit analysis job: {str(e)}",
        )


# ── Poll job result ───────────────────────────────────────────────────────────
@app.get(
    "/results/{job_id}",
    response_model=JobResultResponse,
    summary="Get Analysis Result",
)
def get_job_result(job_id: str, db: Session = Depends(get_db)):
    """
    Retrieve the status and result of an analysis job.

    - **PENDING**: Job is queued, not yet started.
    - **PROCESSING**: Celery worker is running the AI analysis.
    - **COMPLETED**: Analysis is done — `result` field contains the full report.
    - **FAILED**: Analysis failed — `error` field contains the reason.
    """
    job: AnalysisJob | None = db.query(AnalysisJob).filter(AnalysisJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job '{job_id}' not found. Verify the job_id returned from POST /analyze.",
        )
    return JobResultResponse(
        job_id=job.id,
        query=job.query,
        filename=job.filename,
        status=job.status,
        result=job.result,
        error=job.error,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


# ── List all jobs ─────────────────────────────────────────────────────────────
@app.get(
    "/jobs",
    response_model=JobListResponse,
    summary="List All Analysis Jobs",
)
def list_jobs(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Results per page"),
    status: str | None = Query(
        default=None,
        description="Filter by status: PENDING, PROCESSING, COMPLETED, FAILED",
    ),
    db: Session = Depends(get_db),
):
    """
    Retrieve a paginated list of all submitted analysis jobs.

    Optionally filter by `status` to see only completed or failed jobs.
    """
    query_obj = db.query(AnalysisJob)
    if status:
        valid_statuses = {"PENDING", "PROCESSING", "COMPLETED", "FAILED"}
        if status.upper() not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{status}'. Must be one of: {', '.join(sorted(valid_statuses))}",
            )
        query_obj = query_obj.filter(AnalysisJob.status == status.upper())

    total = query_obj.count()
    jobs = (
        query_obj.order_by(AnalysisJob.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return JobListResponse(
        total=total,
        page=page,
        page_size=page_size,
        jobs=[
            JobResultResponse(
                job_id=j.id,
                query=j.query,
                filename=j.filename,
                status=j.status,
                result=j.result,
                error=j.error,
                created_at=j.created_at,
                updated_at=j.updated_at,
            )
            for j in jobs
        ],
    )


# ── Dev server entry point ────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    # Bug Fix #16: was `uvicorn.run(app, reload=True)` — reload requires a string
    #              app reference when used with --reload. Use the CLI instead.
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)