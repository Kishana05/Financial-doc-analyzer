"""
models.py — SQLAlchemy ORM models.

Table: analysis_jobs
    Stores every analysis request, its processing state, and the final results.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, String, Text, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped

from database import Base


def _utcnow() -> datetime:
    """Return a timezone-aware UTC datetime (avoids deprecation warnings)."""
    return datetime.now(timezone.utc)


class AnalysisJob(Base):
    """Represents one financial-document analysis request."""

    __tablename__ = "analysis_jobs"

    # ── Primary key ──────────────────────────────────────────────────────────
    id: Mapped[str] = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )

    # ── Input data ───────────────────────────────────────────────────────────
    query: Mapped[str] = Column(Text, nullable=False)
    filename: Mapped[Optional[str]] = Column(String(255), nullable=True)

    # ── Status ───────────────────────────────────────────────────────────────
    status: Mapped[str] = Column(
        SQLEnum("PENDING", "PROCESSING", "COMPLETED", "FAILED", name="job_status"),
        nullable=False,
        default="PENDING",
    )

    # ── Output data ──────────────────────────────────────────────────────────
    result: Mapped[Optional[str]] = Column(Text, nullable=True)   # populated on COMPLETED
    error: Mapped[Optional[str]] = Column(Text, nullable=True)    # populated on FAILED

    # ── Timestamps ───────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = Column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    def __repr__(self) -> str:
        return f"<AnalysisJob id={self.id!r} status={self.status!r}>"
