# Nytia Recommender

Wellness service recommendation engine for Nytia Labs.

[![CI](https://github.com/rahulsharma-fullstack/NytiaLab/actions/workflows/ci.yml/badge.svg)](https://github.com/rahulsharma-fullstack/NytiaLab/actions/workflows/ci.yml)

## What it does

Two recommendation flows running off the same data and scoring weights.

**Per-employee (`rules-v1` / `rules-ml-v1`).** Take one employee ID, look up
their Hinsight health profile (contributing factors and chronic conditions),
and return ranked wellness service recommendations with plain-English
reasons. Two service tracks:

- **Preventive (factor services):** target lifestyle factors like sleep, stress, nutrition.
- **Treatment (condition services):** target diagnosed or at-risk chronic conditions.

When a trained ML model is available, predicted high-risk conditions add a
capped boost on top of the rule-based score.

**Org-level (`org-rules-v1`).** Take a tenant ID (a partner organisation
like IBM or Microsoft), aggregate every employee's health records into
workforce-wide condition and factor pressure scores, and return ranked
bulk product recommendations with population-aware reasons such as
`"Targets Mental Illness, affecting 29 of your 30 employees (96.7%)"`.
Buyer is the HR manager, not the employee. Math is the per-employee score
summed across the workforce, so products that help the most people float
to the top.

## Tech stack

- Python 3.12, FastAPI
- PostgreSQL 16 (via SQLAlchemy 2.0 + Alembic)
- scikit-learn (per-employee ML risk-prediction layer)
- uv (package manager)
- Docker Compose (local Postgres + production API image)
- GitHub Actions (CI), pre-commit (ruff + gitleaks)

## Quickstart for the demo

### 1. Start Postgres

```powershell
docker compose up -d postgres
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

The seed inserts 4 tenants and 98 employees (8 original demo employees
under `T_NYTIA_DEMO` plus 30 each for `T_IBM`, `T_MICROSOFT`, `T_ACME`),
plus health records following tenant-specific profiles.

### 4. Run the API

```powershell
uv run uvicorn app.main:app --reload --port 8000
```

### 5. Open the demos

- **Per-employee demo:** http://localhost:8000/demo
- **Org-level demo:** http://localhost:8000/demo/org
- **Swagger docs:** http://localhost:8000/docs
- **Health check:** http://localhost:8000/health

## Endpoints

| Method | Path | Notes |
|--------|------|-------|
| GET | `/` | Root info, advertises both demos |
| GET | `/health` | Liveness probe |
| GET | `/demo` | Per-employee demo UI |
| GET | `/demo/org` | Org-level demo UI |
| GET | `/employees` | Paginated list |
| GET | `/employees/{id}` | Single employee |
| GET | `/employees/{id}/health-records` | Full health history |
| GET | `/products` | Filter by category, service_type, condition, factor |
| GET | `/products/{id}` | Product detail with tags |
| GET | `/recommend/{employee_id}?top_n=5` | Per-employee ranked recommendations |
| GET | `/tenants` | List all tenants |
| GET | `/tenants/{id}` | Single tenant |
| GET | `/tenants/{id}/profile` | Workforce health summary (per-condition + per-factor pressure) |
| GET | `/tenants/{id}/recommendations?top_n=10` | Org-level ranked recommendations |

All error responses share the shape `{"error": "<slug>", "detail": ...}`.
Every response carries an `x-request-id` header.

## Algorithm: per-employee (rules-v1)

For each candidate product, the score is the sum of:

- **Condition matches:** `2.0 * relevance * severity_weight * status_weight`
- **Factor matches:** `1.5 * relevance * severity_weight * status_weight`

Weights: `Very Important = 1.5`, `Important = 1.0`, `Suffering = 1.2`,
`At Risk = 1.0`. Products that match nothing are dropped. Top results are
diversified so both tracks (treatment + preventive) appear when available.
Every generated set is written to the `recommendations` audit table.

See [app/services/scoring.py](app/services/scoring.py) for the
implementation. ML boost (when a model is present) is documented in
[ADR 005](DECISIONS.md).

## Algorithm: org-level (org-rules-v1)

Workforce aggregation reuses the per-employee weights:

1. **Aggregate.** For each condition and factor seen in the tenant's
   records, sum `severity_weight * status_weight` across every record.
   The result is a per-dimension `pressure_score`. Also tally distinct
   employees in `Suffering` vs `At Risk`.
2. **Score products.** For each product condition/factor that matches
   the workforce, add `BASE * relevance * pressure_score` (where `BASE`
   is `CONDITION_MATCH_BASE = 2.0` or `FACTOR_MATCH_BASE = 1.5`).
3. **Reasons.** Each match emits a population-aware line:
   `"Targets {name}, affecting {count} of your {total} employees ({pct}%)"`.

Mathematically the org score is the sum of per-employee scores across the
workforce, so the same weights serve both flows and stay in one place.

See [app/services/org_aggregator.py](app/services/org_aggregator.py),
[app/services/scoring.py](app/services/scoring.py)
(`score_product_for_organization`), and
[app/services/org_recommender.py](app/services/org_recommender.py).
[ADR 011](DECISIONS.md) explains why.

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
  main.py                       FastAPI entry point, middleware, /demo and /demo/org routes
  exceptions.py                 Centralised error handlers
  logging_config.py             JSON log formatter
  rate_limit.py                 slowapi setup
  routers/                      HTTP layer (employees, products, recommendations, organization)
  services/                     Business logic (scoring, recommender, org_aggregator, org_recommender, tenant_service)
  repositories/                 SQL access (employee, product, tenant)
  models/                       SQLAlchemy ORM (employee, tenant, health_record, product, recommendation)
  schemas/                      Pydantic API contracts
  ml/                           RandomForest risk predictor
  static/
    index.html                  Per-employee demo UI
    org.html                    Org-level demo UI
alembic/                        DB migrations
scripts/                        seed_data.py, generate_training_data.py, train_model.py
tests/                          pytest suite
docs/                           architecture + compliance docs
```

Three-role pattern: Router -> Service -> Repository. Routers never touch the
DB directly. Services never know about HTTP. Repositories contain only SQL.
See [docs/architecture.md](docs/architecture.md) for diagrams.

## Status

- Per-employee recommender end-to-end with rules-v1 + optional ML boost (rules-ml-v1)
- Org-level recommender end-to-end with org-rules-v1
- 69 passing tests covering scoring math, ML boost, aggregation, integration
- CI on GitHub Actions
- Two demo UIs: per-employee at `/demo`, org-level at `/demo/org`
- 4 tenants and 98 employees seeded for the org demo
- Cloud Run deployment planned for a later phase (see [DECISIONS.md ADR 007](DECISIONS.md))
- Real tenant isolation (auth + per-tenant query scoping) is an open item: see [docs/compliance.md](docs/compliance.md)
