# Nytia Recommender

Wellness service recommendation engine for Nytia Labs.

[![CI](https://github.com/rahulsharma-fullstack/NytiaLab/actions/workflows/ci.yml/badge.svg)](https://github.com/rahulsharma-fullstack/NytiaLab/actions/workflows/ci.yml)

## What it does

Takes an employee ID, looks up their Hinsight health profile (contributing
factors and chronic conditions), and returns ranked wellness service
recommendations with plain-English reasons. Two service tracks:

- **Preventive (factor services):** target lifestyle factors like sleep, stress, nutrition.
- **Treatment (condition services):** target diagnosed or at-risk chronic conditions.

The current recommender (`rules-v1`) scores each product against an employee's
records using condition match, factor match, severity, and status weights, then
diversifies the top results so both tracks are represented.

## Tech stack

- Python 3.12, FastAPI
- PostgreSQL 16 (via SQLAlchemy 2.0 + Alembic)
- scikit-learn (planned, ML layer)
- uv (package manager)
- Docker Compose (local Postgres)
- GitHub Actions (CI), pre-commit (ruff + gitleaks)

## Quickstart for the demo

### 1. Start Postgres

```powershell
docker compose up -d
```

### 2. Install Python deps

```powershell
uv sync
```

### 3. Apply migrations and seed data

```powershell
uv run alembic upgrade head
uv run python scripts/seed_data.py
```

### 4. Run the API

```powershell
uv run uvicorn app.main:app --reload --port 8000
```

### 5. Open the demo

- **Demo UI:** http://localhost:8000/demo
- **Swagger docs:** http://localhost:8000/docs
- **Health check:** http://localhost:8000/health

## Endpoints

| Method | Path | Notes |
|--------|------|-------|
| GET | `/` | Root info |
| GET | `/health` | Liveness probe |
| GET | `/demo` | Single-page demo UI |
| GET | `/employees` | Paginated list |
| GET | `/employees/{id}` | Single employee |
| GET | `/employees/{id}/health-records` | Full health history |
| GET | `/products` | Filter by category, service_type, condition, factor |
| GET | `/products/{id}` | Product detail with tags |
| GET | `/recommend/{employee_id}?top_n=5` | Ranked recommendations with reasons |

All error responses share the shape `{"error": "<slug>", "detail": ...}`.
Every response carries an `x-request-id` header.

## Algorithm (rules-v1)

For each candidate product, the score is the sum of:

- **Condition matches:** `2.0 * relevance * severity_weight * status_weight`
- **Factor matches:** `1.5 * relevance * severity_weight * status_weight`

Weights: `Very Important = 1.5`, `Important = 1.0`, `Suffering = 1.2`,
`At Risk = 1.0`. Products that match nothing are dropped. Top results are
diversified so both tracks (treatment + preventive) appear when available.
Every generated set is written to the `recommendations` audit table.

See [app/services/scoring.py](app/services/scoring.py) for the implementation.

## Tests

```powershell
uv run pytest
```

In-memory SQLite is used for endpoint tests, so no running Postgres is needed
to run the suite.

## Linting and formatting

Pre-commit hooks run ruff (lint + format), gitleaks, and a few generic checks
on every commit. To run them on demand:

```powershell
uv run pre-commit run --all-files
```

## Project structure

```
app/
  main.py                   FastAPI entry point, middleware, /demo route
  exceptions.py             Centralised error handlers
  logging_config.py         JSON log formatter
  routers/                  HTTP layer
  services/                 Business logic (scoring, recommender, orchestration)
  repositories/             SQL access
  models/                   SQLAlchemy ORM
  schemas/                  Pydantic API contracts
  static/index.html         Demo UI
alembic/                    DB migrations
scripts/seed_data.py        Idempotent seed for local dev
tests/                      pytest suite
```

Three-role pattern: Router -> Service -> Repository. Routers never touch the DB
directly. Services never know about HTTP. Repositories contain only SQL.

## Status (May 2026)

- Working end-to-end recommender with audit logging
- 24 passing tests (scoring math + endpoint integration)
- CI on GitHub Actions
- Demo UI at `/demo`
- ML layer planned (waiting on synthetic training data)
- Cloud Run deployment planned for weeks 10-11
