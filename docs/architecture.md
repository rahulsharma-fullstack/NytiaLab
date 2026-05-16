# Architecture

Plain-English walkthrough of how the system fits together. Two diagrams: the
request flow today, and the ML training and serving loop. Both use ASCII so
they live happily inside the repo.

## 1. Request flow

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
- **Rate limiter** (slowapi): 30/min on `/recommend`, 120/min default.
- **Exception handlers** in `app/exceptions.py`: every error has the
  `{error, detail}` JSON shape with the right HTTP code.

## 2. ML training and serving

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

## 3. Data model

Six business tables plus an alembic version table.

```
employees -------(1:N)------> health_records
                                   ^
                                   | references factor + condition by name

products ---(1:N)---> product_conditions ---(N:1)--- conditions (string enum)
        \---(1:N)---> product_factors    ---(N:1)--- factors    (string enum)

employees + products ----(N:N via)----> recommendations  (audit log)
```

Valid factor and condition names are CHECK-constrained at the DB level.
See `app/models/health_record.py` for the canonical list.

## 4. Tech stack at a glance

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

## 5. Local run topology

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

## 6. Future shape (cloud)

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
