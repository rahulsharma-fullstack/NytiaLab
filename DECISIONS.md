# Architecture Decisions Log

This document captures key technical decisions made during the project,
with the reasoning behind each. Think of it as a "why we did it this way"
reference for your future self and anyone joining later.

Format: Architecture Decision Records (ADR) lite.

---

## ADR 001: Python + FastAPI for Backend

**Date:** 2026-04-24
**Status:** Accepted

### Context
Need a backend framework for a recommendation API involving ML components.

### Decision
Python 3.12 with FastAPI.

### Reasoning
- Python is the native ecosystem for ML (scikit-learn, pandas, numpy).
- FastAPI gives modern async support, automatic OpenAPI/Swagger docs, and
  Pydantic validation out of the box.
- Stakeholder indicated TypeScript preferred but Python acceptable for
  ML-heavy components.

### Alternatives Considered
- **Node.js + Fastify:** Would require learning new stack; split ML into
  separate service.
- **Django:** Heavier than needed for an API-only service.
- **Flask:** Older, less modern DX, no async support.

---

## ADR 002: PostgreSQL for Primary Data Store

**Date:** 2026-04-24
**Status:** Accepted

### Context
Need a database for employees, health records, products, and recommendations.

### Decision
PostgreSQL 16 (local via Docker, prod via Cloud SQL).

### Reasoning
- Data is naturally relational (employees, records, products, M2M tags).
- ACID transactions important for health data integrity.
- Excellent Cloud SQL support on GCP.
- Developer familiarity.
- Supports JSON columns if we need schema flexibility later.

### Alternatives Considered
- **MongoDB:** Document model doesn't fit naturally here.
- **SQLite:** Not production-ready for multi-user, multi-tenant scenarios.

---

## ADR 003: uv for Python Package Management

**Date:** 2026-04-24
**Status:** Accepted

### Context
Need a tool to manage Python dependencies and virtual environments.

### Decision
uv (from Astral).

### Reasoning
- Dramatically faster than pip (written in Rust).
- Unified tool: replaces pip, venv, pip-tools, virtualenv.
- Lock file (uv.lock) ensures reproducible builds.
- Actively developed, becoming the modern Python standard.

### Alternatives Considered
- **pip + venv:** Older, slower, requires multiple tools.
- **Poetry:** Good but slower than uv; less actively developed now.
- **Pipenv:** Mostly superseded by newer options.

---

## ADR 004: Three-role pattern (Router / Service / Repository)

**Date:** 2026-04-26
**Status:** Accepted

### Context
We need a consistent place to put HTTP code, business logic, and SQL.
Mixing them led to hard-to-test code in past projects.

### Decision
Every feature follows three layers:

- `app/routers/` for HTTP only (validation, response shaping).
- `app/services/` for business logic (pure Python, testable).
- `app/repositories/` for SQL via SQLAlchemy.

Routers never touch the DB. Services never know about HTTP. Repositories
never make business decisions.

### Reasoning
- Pure-Python services make unit tests trivial (see `tests/test_scoring.py`).
- Repository layer is the obvious seam if we ever need a read-replica or a
  caching layer.
- Centralised error handlers in `app/exceptions.py` translate service
  exceptions to HTTP responses so routers stay tiny.

---

## ADR 005: Rules-v1 recommender, ML as a boost on top

**Date:** 2026-05-04
**Status:** Accepted

### Context
We need explainable recommendations from day one. ML alone would be a black
box and we have no real training data yet.

### Decision
The recommender has two stages:

1. **Rules-v1**: weighted match on conditions and factors. Deterministic,
   fully explainable, runs without ML.
2. **ML boost** (rules-ml-v1): when a trained model is available, predicted
   high-risk conditions add a capped boost to relevant products and add a
   plain-English ML reason. The rule-based score remains the dominant signal.

### Reasoning
- Sponsor demos need clear reasons. Pure ML would not give them.
- The system has to keep working before the ML model is trained (e.g. fresh
  install, missing pickle, training pipeline broken). Falling back to rules
  is safer than failing.
- Algorithm version is recorded with every audit row so we can re-score the
  history later if we change weights.

---

## ADR 006: Self-generated synthetic training data (placeholder)

**Date:** 2026-05-16
**Status:** Accepted (temporary, will be replaced)

### Context
The teammate responsible for synthetic data has not delivered. Real Hinsight
data is too small to train on. We need to unblock the ML phase without
waiting.

### Decision
`scripts/generate_training_data.py` produces a 5,000-row CSV with realistic
factor-to-condition correlations, hand-tuned via a small set of biological
heuristics. The pipeline (data -> train -> save -> serve) is real; the data
is local.

### Reasoning
- Lets us build and prove the entire ML serving path now.
- The README, the `compliance.md`, and the model reasons all flag this as
  "synthetic, placeholder data". No accuracy claim is made.
- When the teammate's data arrives, only the generation script changes; the
  training script and predictor are independent.

---

## ADR 007: Cloud Run + Cloud SQL (not GKE)

**Date:** 2026-04-30 (sponsor confirmation)
**Status:** Accepted

### Context
Original brief mentioned GKE. For a single-service API with low traffic, GKE
is significant operational overhead.

### Decision
Deploy on Cloud Run + Cloud SQL. Cloud deploy itself is **out of scope** for
the current milestone and will follow once the local stack is locked.

### Reasoning
- Cloud Run scales to zero, has built-in TLS, and is dramatically simpler to
  operate solo.
- Cloud SQL covers all our PostgreSQL needs with automated backups and
  encryption at rest.
- Nouridine approved the simpler path.

---

## ADR 008: HTML + vanilla JS demo UI (not React + Vite + TS)

**Date:** 2026-05-16
**Status:** Accepted

### Context
The 12-week plan put a React + Vite + TypeScript demo UI in Week 11. Time
pressure pulled it forward. A separate build pipeline plus an extra running
process would have added complexity for little benefit.

### Decision
`app/static/index.html`: single file, embedded CSS, vanilla JS, served by
FastAPI itself at `/demo`. Calls the existing JSON endpoints.

### Reasoning
- Zero build step. No Node, no bundler, no second process.
- Still looks polished (cards, badges, score pills) and demonstrates the
  full end-to-end story.
- A future React rewrite can replace `index.html` without touching the
  backend.

---

## ADR 009: Centralised exception handlers + JSON error shape

**Date:** 2026-05-16
**Status:** Accepted

### Context
Routers had repetitive `try/except` blocks translating `EmployeeNotFoundError`
to 404. That broke "router stays tight" (ADR 004).

### Decision
All error translation moved to `app/exceptions.py`. Every error response is
`{"error": "<slug>", "detail": ...}` regardless of source. Routers re-raise
freely.

### Reasoning
- One shape for all errors makes client code easier.
- The slug (e.g. `employee_not_found`, `rate_limit_exceeded`,
  `validation_error`) is more useful than free-form prose.
- Stack traces never leak; unhandled exceptions are logged server-side with
  the request id.

---

## ADR 010: Rate limiting via slowapi, tighter on /recommend

**Date:** 2026-05-16
**Status:** Accepted

### Context
The `/recommend` endpoint pulls the full product catalogue and runs ML
inference. Hot loop callers could starve the DB.

### Decision
`slowapi` keyed by client IP. Default 120/min. `/recommend` capped at 30/min.
Limit excess returns a 429 with `error = "rate_limit_exceeded"`.

### Reasoning
- Per-IP works in-process today. When we move to multiple instances on
  Cloud Run, we will switch to a Redis backend without changing the rule
  syntax.
- 30/min on the heavy endpoint is generous for the demo use case and
  conservative enough to protect the DB.
