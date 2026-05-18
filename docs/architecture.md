# Architecture

Plain-English walkthrough of how the system fits together. Diagrams use
ASCII so they live happily inside the repo.

The codebase serves **two** recommendation flows that share the same
scoring weights:

- **Per-employee** at `/recommend/{employee_id}` plus the `/demo` UI.
- **Org-level** (per-tenant workforce) at `/tenants/{id}/recommendations`
  plus the `/demo/org` UI.

Both walk the same middleware -> router -> service -> repository
pipeline. They differ only in which service runs and what gets aggregated.

## 1. Request flow (per-employee)

```
+--------+         +-------------------+
| Client | HTTPS   |  FastAPI process  |
| browser| ------> |  (uvicorn :8000)  |
+--------+         +-------------------+
                            |
                  (1) request middleware
                            |
                            v
                  +-------------------+
                  | Rate limiter      |  -- 429 if over the per-IP cap
                  | (slowapi)         |
                  +-------------------+
                            |
                            v
                  +-------------------+
                  | Router            |  -- HTTP only: validation, query parsing,
                  | app/routers/*.py  |     hands off to a service
                  +-------------------+
                            |
                            v
                  +-------------------+
                  | Service           |  -- Business logic, no HTTP concepts,
                  | app/services/*.py |     no SQL. Calls repository + scoring
                  +-------------------+      and (for /recommend) the ML predictor.
                            |
              +-------------+-------------+
              v                           v
   +-------------------+        +-------------------+
   | Repository        |        | ML predictor      |
   | app/repositories/ |        | app/ml/predictor  |
   +-------------------+        +-------------------+
              |                           |
              v                           v
   +-------------------+        +-------------------+
   | PostgreSQL 16     |        | data/model.pkl    |
   | (Docker locally,  |        | (RandomForest)    |
   |  Cloud SQL prod)  |        +-------------------+
   +-------------------+
```

### Three-role pattern

The router, service, and repository layers each have a single
responsibility. The handoff brief calls this the **three-role pattern**, and
it is the single most important architectural rule in this codebase:

- **Routers** only do HTTP work: request parsing, schema validation, returning
  a response. No SQL, no business logic.
- **Services** hold the business logic. They are pure Python and easy to
  unit-test. They never know about FastAPI or HTTP.
- **Repositories** are the only place that talks to SQLAlchemy / the DB.
  No business decisions live here.

### Cross-cutting concerns

These are layered on at FastAPI startup in `app/main.py`:

- **CORS** middleware (open in dev; lock down in prod).
- **Request logging** middleware: assigns an `x-request-id`, logs one JSON
  line per request with method, path, status code, duration_ms.
- **Rate limiter** (slowapi): 30/min on `/recommend` AND
  `/tenants/{id}/recommendations`, 120/min default elsewhere.
- **Exception handlers** in `app/exceptions.py`: every error has the
  `{error, detail}` JSON shape with the right HTTP code.

## 2. Request flow (org-level)

```
+--------+         +-------------------+
| Client | HTTPS   |  FastAPI process  |
| (HR    | ------> |  (uvicorn :8000)  |
| buyer) |         +-------------------+
+--------+                  |
                  same middleware stack as above
                            |
                            v
                +----------------------------+
                | Router                     |
                | app/routers/organization.py|
                +----------------------------+
                            |
              (1) validate tenant exists
                            |
                            v
                +-------------------+
                | TenantService     |  -- raises TenantNotFoundError (-> 404)
                | get_tenant(id)    |
                +-------------------+
                            |
                            v
                +-------------------------+
                | OrgRecommenderService   |
                | recommend(tenant, top_n)|
                +-------------------------+
                  |          |             |
                  v          v             v
        +-----------------+ +-----------+ +-----------------------+
        | OrgAggregator   | | Product   | | scoring.              |
        | aggregate_      | | Repository| | score_product_for_    |
        | workforce()     | | list_     | | organization()        |
        +-----------------+ | products  | | rank_products_for_    |
                  |         +-----------+ | organization()        |
                  v               |       +-----------------------+
        +-----------------+       |
        | Employee        |       |
        | Repository      |       v
        | get_all_by_     |  +----------+
        | tenant() with   |  | Postgres |
        | health records  |  +----------+
        +-----------------+
                  |
                  v
              +----------+
              | Postgres |
              +----------+
```

The aggregator runs in **pure Python** today. It pulls every employee
for the tenant (with health records eager-loaded via `selectinload`)
and rolls them up into per-condition and per-factor pressure scores
plus distinct-employee head counts.

### Scale ceiling

Suitable for tenants up to **~1000 employees**. The demo runs 30 per
tenant comfortably. For larger tenants, the right move is to refactor
the aggregator into a SQL `GROUP BY`:

```sql
SELECT health_condition, severity, status, COUNT(DISTINCT employee_id)
FROM health_records hr
JOIN employees e ON e.id = hr.employee_id
WHERE e.tenant_id = :tenant_id
GROUP BY health_condition, severity, status;
```

Both `factor` and `health_condition` already have their own indexes,
and `tenant_id` is indexed on `employees`. Compute the pressure
weights in the SELECT or post-process the grouped rows. This is
deferred until the first real tenant exceeds the limit; see ADR 011.

### Why org math reuses per-employee weights

The pressure score itself is the sum of `severity_weight * status_weight`
across every record. Multiplying it by `CONDITION_MATCH_BASE` or
`FACTOR_MATCH_BASE` and `relevance` gives the same answer you would get
by summing the per-employee score across the workforce. One file
(`scoring.py`) holds the constants; tuning them changes both flows.

## 3. ML training and serving

```
+-------------------------+
| scripts/                |
|   generate_training_    |
|   data.py               |
+-------------------------+
            |
            v
   data/synthetic_training.csv   (5,000 rows, 8 factors + 6 condition labels)
            |
            v
+-------------------------+
| scripts/train_model.py  |
| - 80/20 split           |
| - RandomForestClassifier|
| - precision/recall/AUC  |
+-------------------------+
            |
            +--> data/model_metrics.json   (per-condition metrics)
            |
            v
   data/model.pkl   (joblib pickle: model + factor/condition vocab + version)
            |
            | loaded once on first API call to /recommend
            v
+-------------------------+
| app/ml/predictor.py     |
| RiskPredictor singleton |
+-------------------------+
            |
            | used inside
            v
+-------------------------+
| app/services/recommender.py |
| aggregate factor severity   |
| -> predict_risk             |
| -> rank_products(...,       |
|     risk_scores=...)        |
+-------------------------+
            |
            v
    Recommendations
    + ML boost reasons
    + algorithm_version: rules-ml-v1
```

Notes:

- The model is **not** committed to git. The pickle is regenerated locally or
  in CI. The training script's random seed makes the dataset reproducible.
- If `data/model.pkl` is missing, the predictor returns `None` and the API
  silently falls back to pure `rules-v1` mode. Nothing crashes.

## 4. Data model

Seven business tables plus an alembic version table.

```
tenants  -------(1:N)----->  employees -------(1:N)-----> health_records
                                ^                                 ^
                                | tenant_id FK                    | references factor +
                                |                                 |   condition by name
                                |                                 |
                                v
                          recommendations  (audit log of per-employee runs)
                                ^
                                |
products ---(1:N)---> product_conditions ---(N:1)--- conditions (string enum)
        \---(1:N)---> product_factors    ---(N:1)--- factors    (string enum)
```

- `tenants` is the partner organisation (IBM, Microsoft, etc.). Added in
  the second Alembic migration.
- `employees.tenant_id` is the new FK to `tenants.id`. The legacy
  free-text `employees.tenant` column is kept alongside for backwards
  compatibility; new code should prefer `tenant_id` and the
  `tenant_ref` relationship.
- `employees.id` was widened from `String(10)` to `String(20)` so the
  tenant-prefixed IDs (`E_IBM_001`, `E_MICROSOFT_001`, ...) fit. The
  legacy `E0001`-style IDs continue to fit.
- The `recommendations` audit table is **per-employee only**. Org-level
  recommendations are not currently audited (deliberate, see ADR 011).

Valid factor and condition names are CHECK-constrained at the DB level.
See `app/models/health_record.py` for the canonical list.

## 5. Tech stack at a glance

| Layer | Tool |
|-------|------|
| HTTP | FastAPI + uvicorn |
| Validation | Pydantic v2 |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| DB | PostgreSQL 16 |
| ML | scikit-learn RandomForestClassifier |
| Numerics | numpy, pandas |
| Package manager | uv |
| Container | Python 3.12 slim, multi-stage Dockerfile |
| Lint/format | ruff |
| Tests | pytest + httpx TestClient |
| CI | GitHub Actions |
| Deploy target | Cloud Run + Cloud SQL (deferred to a later phase) |

## 6. Local run topology

`docker compose up` brings up two containers on the same Docker network:

```
+---------------------------+        +---------------------------+
| nytia-postgres            | <----- | nytia-api                 |
| postgres:16-alpine        |  5432  | nytia-recommender:local   |
| volume: nytia_postgres_data|        | /app/data mounted ro from |
+---------------------------+        | the host                  |
                                     | port 8000:8000            |
                                     +---------------------------+
```

The host can reach the API on `http://localhost:8000`. The API reaches
Postgres on `postgres:5432` inside the compose network.

### Demo pages

Two demo UIs served by FastAPI itself from `app/static/`:

| Path | File | Audience | What it shows |
|------|------|----------|---------------|
| `/demo` | `index.html` | Internal | One employee's profile + per-employee recommendations |
| `/demo/org` | `org.html` | HR buyer | One tenant's workforce profile + bulk recommendations |

Both are single-file vanilla JS pages, share the same teal palette and
card layout, and link to each other so it is easy to switch demos.

## 7. Future shape (cloud)

Out of scope for this milestone. Planned:

```
GitHub  --(push)-->  GitHub Actions  --(build)-->  Artifact Registry
                                                          |
                                                          v
                                                     Cloud Run
                                                          |
                                                          v
                                                     Cloud SQL
                                                  + Secret Manager
                                                  + Cloud Logging
```
