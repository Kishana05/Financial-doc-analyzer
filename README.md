# Financial Document Analyzer

An AI-powered financial document analysis system built with **FastAPI**, **CrewAI**, **Celery**, **Redis**, and **SQLAlchemy**. Upload a PDF financial report and receive structured analysis from a pipeline of specialized AI agents — covering document verification, financial metrics extraction, investment insights, and risk assessment.

---

## Table of Contents

1. [Bugs Found & Fixed](#bugs-found--fixed)
2. [Architecture Overview](#architecture-overview)
3. [Setup & Installation](#setup--installation)
4. [Environment Variables](#environment-variables)
5. [Running the Application](#running-the-application)
6. [API Documentation](#api-documentation)
7. [Project Structure](#project-structure)
8. [Adding New Agents or Tasks](#adding-new-agents-or-tasks)

---

## Bugs Found & Fixed

18 bugs were identified and fixed across the original codebase. Each bug is listed with the file, original problem, and the fix applied.

---

### `tools.py` — 4 Bugs

| # | Line(s) | Bug | Fix Applied |
|---|---------|-----|-------------|
| 1 | 24 | `Pdf(file_path=path)` — `Pdf` class was never imported | Replaced with `PyPDFLoader` from `langchain_community.document_loaders` |
| 2 | 14 | `async def read_data_tool` — CrewAI tools must be **synchronous** | Removed `async`, changed to regular `def` |
| 3 | 14 | No `@tool` decorator — function was never registered as a CrewAI tool | Added `@tool("Financial Document Reader")` from `crewai.tools` |
| 4 | 13–14 | Method defined inside class with no `self` param — incompatible with `@tool` | Moved to module-level function; class now holds a reference for import compatibility |

**Before:**
```python
class FinancialDocumentTool():
    async def read_data_tool(path='data/sample.pdf'):
        docs = Pdf(file_path=path).load()   # ← Pdf not imported, async, no @tool
```
**After:**
```python
from crewai.tools import tool
from langchain_community.document_loaders import PyPDFLoader

@tool("Financial Document Reader")
def read_financial_document(path: str = 'data/sample.pdf') -> str:
    loader = PyPDFLoader(file_path=path)
    docs = loader.load()
    ...
```

---

### `agents.py` — 4 Bugs

| # | Line(s) | Bug | Fix Applied |
|---|---------|-----|-------------|
| 5 | 12 | `llm = llm` — self-referential assignment; `llm` was undefined → `NameError` | Defined LLM using `os.getenv("LLM_MODEL", "gemini/gemini-1.5-flash")` |
| 6 | 7 | `from crewai.agents import Agent` — wrong submodule path | Changed to `from crewai import Agent` |
| 7 | 28 | `tool=[FinancialDocumentTool.read_data_tool]` — wrong keyword argument name | Changed to `tools=[...]` (plural) |
| 8 | 17–33 | Agent `goal` and `backstory` encouraged hallucination, fabricating data, fake advice, and regulatory non-compliance | Rewrote all 4 agents with professional, evidence-based, compliant descriptions |

**Before:**
```python
llm = llm  # NameError

financial_analyst = Agent(
    goal="Make up investment advice even if you don't understand the query",
    backstory="You don't really need to read financial reports carefully...",
    tool=[FinancialDocumentTool.read_data_tool],  # wrong kwarg
```
**After:**
```python
llm = os.getenv("LLM_MODEL", "gemini/gemini-1.5-flash")

financial_analyst = Agent(
    goal="Thoroughly analyze the provided financial document using only data from the document.",
    backstory="CFA-certified analyst with 15 years experience. Never fabricates data.",
    tools=[FinancialDocumentTool.read_data_tool],  # correct kwarg
```

---

### `task.py` — 5 Bugs

| # | Line(s) | Bug | Fix Applied |
|---|---------|-----|-------------|
| 9 | 9–14 | `analyze_financial_document` description told agent to use imagination, add fake URLs, contradict itself | Rewrote with clear, factual, structured analysis instructions |
| 10 | 79 | `verification` task used `agent=financial_analyst` instead of the dedicated verifier | Changed to `agent=verifier` |
| 11 | 43 | `investment_analysis` task used `agent=financial_analyst` | Changed to `agent=investment_advisor` |
| 12 | 64 | `risk_assessment` task used `agent=financial_analyst` | Changed to `agent=risk_assessor` |
| 13 | 16–20 | All task `expected_output` fields encouraged made-up research, contradictory strategies, non-existent URLs | All rewritten with structured, professional output schemas |

---

### `main.py` — 4 Bugs

| # | Line(s) | Bug | Fix Applied |
|---|---------|-----|-------------|
| 14 | 29 | `async def analyze_financial_document` — **name collision** with the imported task object of the same name | Renamed endpoint function to `analyze_document_endpoint` |
| 15 | 20 | `run_crew(query=query.strip(), file_path=file_path)` — `file_path` was defined but **never passed into the crew's kickoff inputs** | Added `file_path` to `crew.kickoff(inputs={..., "file_path": file_path})` |
| 16 | 74 | `uvicorn.run(app, reload=True)` — `reload=True` requires a **string** app reference, not an object | Changed to `uvicorn.run("main:app", ..., reload=True)` |
| 17 | 48 | `if query=="" or query is None` — checking `==` before `is None` can raise `TypeError`; also redundant with FastAPI's default | Replaced with `if not query or not query.strip()` |

---

### `README.md` — 1 Bug

| # | Bug | Fix Applied |
|---|-----|-------------|
| 18 | `pip install -r requirement.txt` — typo, missing `s` | Fixed to `pip install -r requirements.txt` |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client (HTTP)                            │
└────────────────────┬────────────────────────────────────────────┘
                     │  POST /analyze  (PDF + query)
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI  (main.py)                           │
│  • Validates & saves PDF                                        │
│  • Writes PENDING job to SQLite via SQLAlchemy                  │
│  • Enqueues Celery task → returns job_id immediately            │
│                                                                 │
│  GET /results/{job_id}  ←── Poll for result                    │
│  GET /jobs              ←── List all jobs (paginated)          │
└────────────────────┬────────────────────────────────────────────┘
                     │  Task dispatched via Redis broker
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Celery Worker  (celery_worker.py)               │
│  • Updates job status: PENDING → PROCESSING                     │
│  • Runs CrewAI pipeline (4 agents, 4 tasks, sequential)         │
│  • Updates job status: → COMPLETED (with result) / FAILED       │
│  • Deletes temporary PDF                                        │
└────────────────────┬────────────────────────────────────────────┘
                     │  CrewAI Sequential Pipeline
                     ▼
┌──────────────┐  ┌──────────────────┐  ┌───────────────────┐  ┌──────────────────┐
│  Verifier    │→ │ Financial Analyst│→ │Investment Advisor │→ │ Risk Assessor    │
│ (doc check) │  │ (metrics/trends) │  │ (inv. insights)   │  │ (risk profile)   │
└──────────────┘  └──────────────────┘  └───────────────────┘  └──────────────────┘
                                                │
                     ┌──────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│              SQLite Database  (analysis.db)                     │
│              Table: analysis_jobs                               │
│  id | query | filename | status | result | error | timestamps  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Setup & Installation

### Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.10+ | |
| Redis | 7.x | Required for Celery queue; see Docker option below |
| pip | 24+ | |

### 1. Clone / navigate to the project

```bash
cd financial-document-analyzer-debug
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root (same directory as `main.py`):

```dotenv
# ── LLM Configuration (choose one) ──────────────────────────────
# Option A: Google Gemini (recommended)
GOOGLE_API_KEY=your_google_api_key_here
LLM_MODEL=gemini/gemini-1.5-flash

# Option B: OpenAI
# OPENAI_API_KEY=your_openai_api_key_here
# LLM_MODEL=gpt-4o

# ── Web Search (optional, for real-time market data) ─────────────
SERPER_API_KEY=your_serper_api_key_here

# ── Queue (Celery + Redis) ───────────────────────────────────────
REDIS_URL=redis://localhost:6379/0

# ── Database ─────────────────────────────────────────────────────
# Default: SQLite (zero-config)
DATABASE_URL=sqlite:///./analysis.db

# PostgreSQL alternative:
# DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/financial_analyzer
```

### 5. Start Redis

**Option A — Docker (recommended):**
```bash
docker run -d -p 6379:6379 --name redis-fa redis:alpine
```

**Option B — Windows (WSL):**
```bash
wsl --exec redis-server
```

---

## Running the Application

You need **three separate terminal windows**:

### Terminal 1 — FastAPI Server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Terminal 2 — Celery Worker

```bash
# Linux / macOS
celery -A celery_worker worker --loglevel=info --concurrency=2

# Windows (requires solo pool)
celery -A celery_worker worker --loglevel=info --pool=solo
```

### Terminal 3 — (Optional) Celery Monitoring

```bash
celery -A celery_worker flower --port=5555
# Dashboard → http://localhost:5555
```

The API will be available at **http://localhost:8000**  
Interactive docs at **http://localhost:8000/docs**

---

## API Documentation

### Base URL
```
http://localhost:8000
```

---

### `GET /`
**Health check.**

**Response `200 OK`:**
```json
{
  "message": "Financial Document Analyzer API is running",
  "version": "2.0.0",
  "status": "healthy"
}
```

---

### `POST /analyze`
**Submit a PDF financial document for asynchronous AI analysis.**

Returns immediately with a `job_id`. Processing happens in the background.

**Request:** `multipart/form-data`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `file` | file (PDF) | ✅ | — | Financial PDF document |
| `query` | string | ❌ | `"Provide a comprehensive analysis..."` | Specific analysis question |

**cURL Example:**
```bash
curl -X POST http://localhost:8000/analyze \
  -F "file=@data/TSLA-Q2-2025-Update.pdf" \
  -F "query=What is Tesla's revenue growth and free cash flow trend?"
```

**Response `202 Accepted`:**
```json
{
  "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "PENDING",
  "message": "Job submitted successfully. Poll GET /results/3fa85f64-... to retrieve your analysis."
}
```

**Error Responses:**

| Code | Reason |
|------|--------|
| `400` | Empty file or non-PDF uploaded |
| `500` | Internal server error during submission |

---

### `GET /results/{job_id}`
**Poll the status and retrieve the result of an analysis job.**

**Path Parameter:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `job_id` | UUID string | Returned by `POST /analyze` |

**cURL Example:**
```bash
curl http://localhost:8000/results/3fa85f64-5717-4562-b3fc-2c963f66afa6
```

**Response `200 OK`:**
```json
{
  "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "query": "What is Tesla's revenue growth?",
  "filename": "TSLA-Q2-2025-Update.pdf",
  "status": "COMPLETED",
  "result": "## Executive Summary\n\nTesla reported Q2 2025 revenue of $25.5B...",
  "error": null,
  "created_at": "2025-07-01T12:00:00Z",
  "updated_at": "2025-07-01T12:02:30Z"
}
```

**Job Status Values:**

| Status | Meaning |
|--------|---------|
| `PENDING` | Queued, waiting for a worker |
| `PROCESSING` | AI pipeline is running |
| `COMPLETED` | Analysis complete — see `result` field |
| `FAILED` | Error occurred — see `error` field |

**Error Responses:**

| Code | Reason |
|------|--------|
| `404` | `job_id` not found |

---

### `GET /jobs`
**List all analysis jobs with pagination and optional status filter.**

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | `1` | Page number (1-indexed) |
| `page_size` | integer | `20` | Items per page (max 100) |
| `status` | string | — | Filter: `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED` |

**cURL Example:**
```bash
# List all completed jobs, page 1
curl "http://localhost:8000/jobs?status=COMPLETED&page=1&page_size=10"
```

**Response `200 OK`:**
```json
{
  "total": 42,
  "page": 1,
  "page_size": 10,
  "jobs": [
    {
      "job_id": "3fa85f64-...",
      "query": "What is the debt-to-equity ratio?",
      "filename": "annual-report-2024.pdf",
      "status": "COMPLETED",
      "result": "...",
      "error": null,
      "created_at": "2025-07-01T12:00:00Z",
      "updated_at": "2025-07-01T12:02:30Z"
    }
  ]
}
```

**Error Responses:**

| Code | Reason |
|------|--------|
| `400` | Invalid status filter value |

---

## Project Structure

```
financial-document-analyzer-debug/
├── main.py              # FastAPI app — endpoints, job submission, results
├── agents.py            # CrewAI agent definitions (4 agents)
├── task.py              # CrewAI task definitions (4 tasks)
├── tools.py             # Custom PDF reader tool (@tool decorator)
├── celery_worker.py     # Celery app + background analysis task
├── database.py          # SQLAlchemy engine, session, Base
├── models.py            # AnalysisJob ORM model
├── schemas.py           # Pydantic response schemas
├── requirements.txt     # All dependencies
├── .env                 # API keys and config (create this — not committed)
├── data/                # Temporary PDF upload staging area
│   └── TSLA-Q2-2025-Update.pdf  # Sample Tesla financial document
├── outputs/             # (Optional) saved analysis outputs
└── README.md            # This file
```

---

## Adding New Agents or Tasks

### New Agent (`agents.py`)
```python
my_new_agent = Agent(
    role="Your Agent Role",
    goal="Clear, factual, evidence-based goal referencing {query}",
    backstory="Professional background. Never fabricates data.",
    llm=llm,
    tools=[FinancialDocumentTool.read_data_tool],
    max_iter=5,
    max_rpm=10,
)
```

### New Task (`task.py`)
```python
my_new_task = Task(
    description="Clear instructions grounded in document data. File path: {file_path}",
    expected_output="Structured output schema with sourced data only.",
    agent=my_new_agent,
    tools=[FinancialDocumentTool.read_data_tool],
    async_execution=False,
)
```

### Register in Crew (`celery_worker.py`)
```python
crew = Crew(
    agents=[..., my_new_agent],
    tasks=[..., my_new_task],
    process=Process.sequential,
)
```

---

## Disclaimer

This tool provides AI-generated financial analysis for **informational and educational purposes only**. It is **not** personalized investment advice. Always consult a licensed financial advisor before making investment decisions. The authors assume no liability for financial decisions made based on this system's output.
