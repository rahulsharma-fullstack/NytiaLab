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

Rewrote `README.md` so it works as the demo-day briefing:
- CI badge.
- Plain-English "what it does".
- 5-step Quickstart: docker compose up, uv sync, alembic upgrade, seed, uvicorn.
- Endpoint table.
- One-paragraph rules-v1 explanation with the weights spelled out.
- Project structure overview with the three-role pattern.
- Status section (current vs planned).

---

## Day 8-9 continuation (after demo plan was scrapped)

User instruction: complete the project except cloud parts. New work below.

### Phase A: rate limiting

New dep: `slowapi` (`uv add slowapi`).

New file:
- `app/rate_limit.py` - configures a `Limiter` keyed by client IP, defines `DEFAULT_LIMIT = "120/minute"` and `RECOMMEND_LIMIT = "30/minute"`, exposes `install_rate_limiter(app)` that wires the limiter, middleware, and a JSON 429 handler with the same `{error, detail}` shape as the other handlers.

Changed:
- `app/main.py` - calls `install_rate_limiter(app)`.
- `app/routers/recommendations.py` - the recommend endpoint now takes `request: Request` and is decorated with `@limiter.limit(RECOMMEND_LIMIT)`. Tighter cap on the heavy endpoint.

Tests:
- New `test_recommend_rate_limit_returns_429` in `tests/test_endpoints.py` - hits `/recommend/E0001` 35 times in a row and asserts at least one 429 with `error = "rate_limit_exceeded"`.
- `uv run pytest` -> **25 passed**.

### Phase B: ML risk-prediction layer

The teammate has not delivered synthetic training data yet, so I generated my own as a placeholder. The pipeline is real; the data is local.

New deps: `scikit-learn`, `pandas`, `joblib`.

**B1. Generate synthetic training data**
- `scripts/generate_training_data.py` - 5,000 rows. Inputs: 8 factor severity scores (continuous 0..1, Beta(2,3) distribution). Outputs: 6 binary chronic-condition labels. Risk for each condition is a hand-tuned weighted sum of relevant factors -> sigmoid -> Bernoulli draw. Wellness is internally inverted (high wellness = low contribution to risk) and is also slightly anti-correlated with depression to be a bit realistic. Random seed 42 for reproducibility.
- Saved to `data/synthetic_training.csv` (~832 KB). Condition prevalence: CVD 65%, T2D 42%, CKD 22%, Cancer 20%, MI 58%, Osteo 29%.

**B2. Train RandomForest model**
- `scripts/train_model.py` - one multi-output `RandomForestClassifier` (n_estimators=100, max_depth=12, min_samples_leaf=5) predicts all 6 conditions in one shot. 80/20 train/test split. Per-condition precision, recall, f1, ROC-AUC, and positive rate saved to `data/model_metrics.json`. Model + feature/label metadata pickled to `data/model.pkl` via joblib.
- Metrics summary: AUC 0.60-0.66 across conditions on synthetic data. Precision/recall at the 0.5 threshold is weak on rare classes (CKD, Cancer) which is expected - we use the model as a *probability source* for boosting, not for hard classification.

**B3. Predictor module**
- New `app/ml/predictor.py`:
  - `RiskPredictor` class wraps the loaded model and the factor / condition label vocabularies.
  - `RiskPredictor.from_disk()` returns `None` if the pickle is missing; the API keeps working in pure rules mode in that case.
  - `get_predictor()` is a lazy, thread-safe singleton accessor.
  - `aggregate_factor_severity(records)` collapses a list of `HealthRecord` rows into a single severity score per factor in 0..1. Factors not reported fall back to the population baseline (~0.4) rather than 0, because "no record" is not the same as "perfectly healthy".
  - DB-name <-> model-feature-name mapping tables (`FACTOR_LABEL_TO_DB`, `CONDITION_LABEL_TO_DB`).
- `app/ml/__init__.py` exposes the public surface.

**B4. Recommender integration**
- `app/services/scoring.py`:
  - New constants: `ML_ALGORITHM_VERSION = "rules-ml-v1"`, `ML_RISK_BOOST_BASE = 1.5`, `ML_RISK_PROB_THRESHOLD = 0.6`.
  - `score_product_for_employee` takes an optional `risk_scores: dict[str, float]` argument. For each predicted condition above 0.6, if the employee does *not* already have that condition in their records and the product targets it, add a boost of `1.5 * relevance * probability` and append an ML reason line.
  - `rank_products` plumbs the risk dict through.
- `app/services/recommender.py`:
  - On every call, asks `get_predictor()`. If it returns a predictor, runs `aggregate_factor_severity` + `predict_risk` and passes the result into `rank_products`. The bundle's `algorithm_version` becomes `rules-ml-v1`; otherwise it stays `rules-v1`.
  - `_log_recommendations` now takes the algorithm version as a parameter so the audit table records exactly which algo produced each row.

**B5. Tests + drift fix**
- New `tests/test_ml.py` - 11 tests covering `aggregate_factor_severity` (mapping, max-per-factor, baseline fill, unknown factor handling), predictor load behavior (None when no pickle, real predictor otherwise), `predict_risk` output shape and responsiveness to inputs, and scoring boost rules (below threshold no-op, above threshold boost + reason, no double-count when employee already has the condition).
- Fixed `test_recommend_for_employee_returns_ranked_results` in `tests/test_endpoints.py` - the `algorithm_version` assertion now accepts either `rules-v1` or `rules-ml-v1` because the predictor loads automatically when the pickle is present.

**Live sanity checks against the real Postgres:**
- E0001 (Sleep + Stress + CVD): ML adds "elevated Mental Illness risk (64%)" boost to Sleep Hygiene and Mindfulness products. Top recommendation is now Sleep Hygiene Coaching.
- E0003 (Nutrition + CKD, single record): ML adds "elevated Cardiovascular Disease risk (72%)" boost. Pulls Nutrition Counseling and Mindfulness/Sleep into the top results.
- E0002 (already multi-condition): no ML boosts surface because all the high-risk conditions are already direct matches.

`uv run pytest` -> **36 passed**.

### Phase C: Containerization

**C1. Production `Dockerfile`**
Multi-stage build (builder + runtime), Python 3.12 slim, non-root user `app`, `HEALTHCHECK` hitting `/health` every 30s.

- Builder stage: copies uv from the official `ghcr.io/astral-sh/uv:0.5.11` image (no apt needed), copies `pyproject.toml` + `uv.lock` first for layer caching, then `app/`, `alembic/`, `scripts/`. Two `uv sync` calls so dep-only layers stay cached when only source code changes.
- Runtime stage: only `libpq5` + `curl` from apt (for psycopg2 + healthcheck), copies the prebuilt venv (`/opt/venv`) and the application from the builder. `PATH` points at the venv.
- Final image size: 757 MB. Most of that is numpy + scipy + scikit-learn; could be cut later by switching to a non-ML container variant if needed.

**C2. `.dockerignore`**
Drops .git, .venv, tests, docs, model data, IDE state, README/markdown, and other dev-only files. Keeps build context small.

**C3. Updated `docker-compose.yml`**
Adds an `api` service that builds the `Dockerfile`, depends on `postgres` being healthy, sets env vars for the DB inside the docker network (`DB_HOST=postgres`), publishes port 8000, and runs `alembic upgrade head && uvicorn ...` as its command so migrations apply on every start.

`./data` is mounted read-only into the container at `/app/data` so the ML model can be loaded if it was generated locally first.

**Live smoke test:**
- `docker build -t nytia-recommender:local .` -> success in ~20s after caches.
- `docker compose up -d` -> Postgres healthy, API healthy.
- `curl http://localhost:8000/health` -> 200 with `{"status":"healthy",...}`.
- `curl http://localhost:8000/recommend/E0002?top_n=3` -> 200, `algorithm_version: "rules-ml-v1"`, sensible top-3 (Mental Health Therapy, Mindfulness App, Nutrition Counseling).
- `curl http://localhost:8000/demo` -> 200 with the index.html shell.

### Phase D: Docs + decision log

New files:
- `docs/compliance.md` - PIPEDA principles mapped to what the code does, HIPAA-style controls (access, audit, transport, validation, error handling), ML-specific notes (synthetic data flagged), and an open-items checklist (retention policy, auth, self-serve history, Secret Manager).
- `docs/architecture.md` - request-flow diagram (Client -> CORS -> request logger -> rate limiter -> Router -> Service -> Repository -> Postgres + ML predictor sidecar), ML training/serving diagram, data model relationships, tech stack table, local docker compose topology, and a thumbnail of the future cloud shape.

Updated:
- `DECISIONS.md` - added seven new ADRs:
  - 004 Three-role pattern
  - 005 Rules-v1 + ML boost (rules-ml-v1)
  - 006 Self-generated synthetic training data (placeholder)
  - 007 Cloud Run + Cloud SQL (not GKE)
  - 008 HTML + vanilla JS demo UI (not React + Vite)
  - 009 Centralised exception handlers + {error, detail} shape
  - 010 Rate limiting via slowapi, tighter on /recommend

### Final smoke test

End-to-end check against the live `nytia-api` container talking to `nytia-postgres`:

- `uv run pytest` -> **36 passed**.
- `uv run ruff check .` + `uv run ruff format --check .` -> clean (after `--fix`).
- `curl http://localhost:8000/health` -> 200, `{"status":"healthy",...}`.
- `curl http://localhost:8000/employees` -> 200, 8 employees returned.
- `/recommend/{id}?top_n=1` for E0001..E0008 (all `rules-ml-v1`):

  | Employee | Top recommendation |
  |---------|--------------------|
  | E0001 | Cardiac Rehabilitation Program (7.08) |
  | E0002 | Mental Health Therapy Sessions (6.30) |
  | E0003 | Nutrition Counseling Service (3.46) |
  | E0004 | Mental Health Therapy Sessions (6.30) |
  | E0005 | Smoking Cessation Program (4.31) |
  | E0006 | Physical Activity Tracker + Coach (4.43) |
  | E0007 | Sleep Hygiene Coaching Program (3.70) |
  | E0008 | Physical Activity Tracker + Coach (4.55) |

Each top pick is consistent with the employee's profile (e.g. E0008 has Movement + Osteoporosis and the top rec is a movement device; E0002 has severe depression + mental illness and the top rec is therapy).

---

## What is complete vs what is still ahead

**Done in this session (Days 8-9 + ML phase + containerization + docs):**

- API hardening: structured JSON logging, central error handlers with `{error, detail}` shape, request-id middleware, CORS, rate limiting (slowapi).
- ML risk-prediction layer (`rules-ml-v1`): synthetic data generator, RandomForest training script, predictor with lazy thread-safe loading, integration into the recommender with capped boosts and plain-English ML reasons. Falls back to `rules-v1` if the model pickle is missing.
- Containerization: multi-stage Dockerfile, non-root user, healthcheck, `.dockerignore`, compose service that runs migrations + uvicorn together.
- Tests: 36 passing across scoring, ranking, ML predictor + boost rules, endpoint integration (including 429 rate limit), and the demo HTML route.
- Docs: README, `docs/compliance.md`, `docs/architecture.md`, expanded `DECISIONS.md`.
- CI: GitHub Actions running ruff + tests on every push to main and on PRs.
- Demo UI at `/demo`.

**Deferred (user will handle the cloud phase later):**

- Cloud Run deployment.
- Cloud SQL instance + IAM.
- Cloud Build pipeline.
- Artifact Registry + image signing.
- Secret Manager for credentials.
- Trivy scanning.

**Still blocked on others:**

- Teammate's real synthetic training data (we are using a placeholder generated locally).
- Nouridine clarification on the data-dictionary-vs-record-level question and direct Hinsight DB access.
