# Demo Progress Log

This file tracks all work done to get the project ready for tomorrow's sponsor demo.

## Demo Goal

Walk Nouridine through a working wellness recommendation engine:

1. Open a simple web page in the browser.
2. Pick an employee from a dropdown.
3. See their health profile (factors, conditions, severity, status).
4. See ranked wellness service recommendations with plain-English reasons.
5. Show the API docs (Swagger) for engineering credibility.
6. Show tests, CI, error handling, logs for production-readiness story.

## Scope For Today (Day 8 push)

What I am doing now, in priority order. Each step ends with a `git commit` so we can stop any time and still have a working demo.

| # | Task | Status |
|---|------|--------|
| 1 | Finish 7 ready scoring + rank_products unit tests | pending |
| 2 | Add error handling middleware + CORS to FastAPI | pending |
| 3 | Add structured JSON logging | pending |
| 4 | Add endpoint integration tests with TestClient (SQLite in-memory) | pending |
| 5 | Add an `/employees/{id}/profile` summary endpoint (UI helper) | pending |
| 6 | Build simple HTML + vanilla JS demo UI served by FastAPI | pending |
| 7 | Add GitHub Actions CI workflow (lint + tests) | pending |
| 8 | Polish README with demo run instructions | pending |
| 9 | Smoke test end-to-end | pending |

## Changes vs the Original 12-Week Plan

- **Frontend:** Original plan was React + Vite + TypeScript in Week 11. For time, I am using a single HTML page with vanilla JS, served by FastAPI as a static file. No build step, no second process. Same FastAPI server, one extra URL: `/demo`. Can be replaced with React later without changing the backend.
- **ML layer:** Skipped. Was Week 5+. Still blocked on synthetic data from teammate. Demo runs on the rules-v1 recommender, which already gives strong, explainable results.
- **Cloud deployment:** Skipped. Was Week 10-11. Demo runs locally on `localhost:8000`.
- **Containerization (production):** Skipped. Was Week 8-9. We still have the dev Docker Compose for Postgres.

## What Was Already Built Before Today

- FastAPI app with 4 routers (`/health`, `/employees`, `/products`, `/recommend`)
- Postgres 16 via Docker Compose, 6 business tables + alembic version
- Three-role architecture (Router > Service > Repository) applied everywhere
- Rules-v1 recommender with diversity post-processing and audit logging
- Seed data: 8 employees, 12 health records, 12 products
- Pre-commit hooks: ruff lint + format, gitleaks, trailing whitespace, YAML/TOML validation
- 2 scoring tests passing

## Detailed Log

Entries are appended below as I work. Each entry has a timestamp, what I did, and what file(s) changed.

---

### Step 0 (planning)

- Read `app/main.py`, `app/services/scoring.py`, `app/services/recommender.py`, `app/routers/recommendations.py`, `app/routers/employees.py`, `tests/test_scoring.py`, `scripts/seed_data.py`, `app/schemas/recommendation.py`.
- Confirmed recommender works end-to-end and matches handoff doc.
- Created this progress log.
