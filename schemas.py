"""
schemas.py — Pydantic v2 schemas for request validation and API responses.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Response: job submission ──────────────────────────────────────────────────
class JobSubmittedResponse(BaseModel):
    """Returned immediately after a document is submitted for analysis."""
    job_id: str = Field(..., description="Unique identifier for the analysis job")
    status: str = Field("PENDING", description="Initial job status")
    message: str = Field(..., description="Human-readable confirmation message")

    model_config = {"from_attributes": True}


# ── Response: single job status / result ─────────────────────────────────────
class JobResultResponse(BaseModel):
    """Full job details including result once processing is complete."""
    job_id: str = Field(..., description="Unique job identifier")
    query: str = Field(..., description="Original user query")
    filename: Optional[str] = Field(None, description="Uploaded file name")
    status: str = Field(..., description="PENDING | PROCESSING | COMPLETED | FAILED")
    result: Optional[str] = Field(None, description="Analysis result (populated when COMPLETED)")
    error: Optional[str] = Field(None, description="Error message (populated when FAILED)")
    created_at: datetime = Field(..., description="Timestamp when the job was created (UTC)")
    updated_at: datetime = Field(..., description="Timestamp of last status update (UTC)")

    model_config = {"from_attributes": True}


# ── Response: paginated job list ─────────────────────────────────────────────
class JobListResponse(BaseModel):
    """Paginated list of all analysis jobs."""
    total: int = Field(..., description="Total number of jobs in the database")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of items per page")
    jobs: list[JobResultResponse] = Field(..., description="Jobs on this page")
