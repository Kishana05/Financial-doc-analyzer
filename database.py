"""
database.py — SQLAlchemy engine, session factory, and Base.

Database URL is read from the DATABASE_URL environment variable.
Defaults to SQLite (zero-config for local development).
To switch to PostgreSQL set:  DATABASE_URL=postgresql+psycopg2://user:pass@host/dbname
"""
import os
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# ── Connection URL ────────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./analysis.db")

# SQLite needs check_same_thread=False for multi-threaded use (FastAPI / Celery)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

# ── Session factory ───────────────────────────────────────────────────────────
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ── Base class for ORM models ─────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── FastAPI dependency ────────────────────────────────────────────────────────
def get_db():
    """Yield a database session and ensure it is closed after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables (called at application startup)."""
    # Import models here so they are registered on Base.metadata before create_all
    from models import AnalysisJob  # noqa: F401
    Base.metadata.create_all(bind=engine)
