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

### Step 1: scoring + ranking unit tests

- Added 7 tests to `tests/test_scoring.py`: factor match math, condition vs factor priority, severity weight, status weight, combined scoring, `rank_products` top_n, `rank_products` zero-score filter.
- `uv run pytest` -> 9 passed.
- Commit: `test: add scoring and ranking unit tests` (pushed to main).

### Step 2: error handling, CORS, structured logging, request middleware

Decision: bundled three middleware-style concerns into one commit since they all touch `app/main.py`.

New files:
- `app/exceptions.py` - handlers for `EmployeeNotFoundError`, `ProductNotFoundError`, `StarletteHTTPException`, `RequestValidationError`, and a catch-all `Exception` -> 500 with JSON. All responses now have a stable `{error, detail}` shape.
- `app/logging_config.py` - `JsonFormatter` + `configure_logging()`. Emits one JSON line per log record on stdout. No third-party deps.

Changed:
- `app/main.py`:
  - Calls `configure_logging()` at import time.
  - Adds `CORSMiddleware` (open for the demo - lock down for prod later).
  - Adds `RequestLoggingMiddleware` that logs method/path/status/duration with a generated `x-request-id` header on each response.
  - Registers all exception handlers via `register_exception_handlers(app)`.
  - Root `/` now also advertises the future `/demo` UI URL.

Smoke checks:
- `uv run python -c "from app.main import app"` - imports cleanly.
- `uv run pytest` - still 9 passed.

### Step 3: endpoint integration tests with TestClient

New files:
- `tests/conftest.py` - in-memory SQLite engine + sessionmaker, `db_session` fixture, `client` fixture (overrides `get_db`), `seeded_db` fixture with 2 employees, 2 health records, 3 products.
- `tests/test_health.py` - root, /health, x-request-id header.
- `tests/test_endpoints.py` - 11 tests covering employees list/get/missing/health-records, products list + filter by condition + filter by service_type, recommend ranked + top_n + missing employee + invalid top_n.

Cleanup (made centralised error handlers actually work):
- `app/routers/employees.py`, `app/routers/products.py`, `app/routers/recommendations.py` - removed router-level try/except. Services raise `EmployeeNotFoundError`/`ProductNotFoundError` and the global handlers in `app/exceptions.py` translate them to clean 404 JSON.

Result:
- `uv run pytest` -> **23 passed**.

### Step 4: seed data review (no changes needed)

Reviewed existing seed data:
- 8 employees across Ontario regions
- 12 health records covering each of the 6 conditions + most of the 8 factors
- 12 products (6 factor-services + 6 condition-services)
- Each employee tells a distinct story: heart-risk (E0001), multi-issue severe (E0002), preventive (E0003), single severe mental health (E0004), cancer (E0005), diabetes (E0006), multi-at-risk (E0007), bone health (E0008).

Decision: skip changes. Variety is already strong for the demo. Time is better spent on the UI.

### Step 5: simple demo UI served by FastAPI

New file:
- `app/static/index.html` - single-page demo UI. Embedded CSS, vanilla JS. No build step.

Layout:
- Top bar with the title and tagline.
- Controls row: employee dropdown + top-N input + algorithm version label.
- Two cards side-by-side (stacks on narrow screens):
  - **Health profile**: region badge, 3 KPI tiles (conditions / factors / suffering count), and a table of health records with severity + status badges.
  - **Top recommendations**: ranked list with a numbered chip, name, category + price, a coloured "Treatment" / "Preventive" badge, a score pill, and a bullet list of plain-English reasons.

JS calls three existing endpoints in parallel: `/employees/{id}`, `/employees/{id}/health-records`, `/recommend/{id}?top_n=N`. Errors render a red banner.

Changes in `app/main.py`:
- Mount `app/static/` at `/static`.
- New `/demo` route serves `static/index.html` via `FileResponse`.
- Root `/` advertises `/demo` and `/docs`.
- Both `/` and `/demo` are `include_in_schema=False` so they do not clutter Swagger.

Tests:
- Added `test_demo_page_serves_html` to `tests/test_health.py`.
- `uv run pytest` -> **24 passed**.

### Step 6: GitHub Actions CI

New file:
- `.github/workflows/ci.yml` - runs on push to `main` and on PRs to `main`.
  - Sets up Python 3.12 + uv (with uv cache enabled)
  - `uv sync --frozen`
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run pytest -v`

Verified locally before commit:
- `uv run ruff check .` -> All checks passed
- `uv run ruff format --check .` -> 39 files already formatted
- `uv run pytest` -> 24 passed

### Step 7: README polish
