# Compliance notes

> Status: first-pass mapping for the Nytia Labs recommender. PIPEDA (Canada)
> is the primary regime for Nytia; HIPAA (US) principles are referenced
> because most health-data engineering practice describes itself in HIPAA
> terms. Final compliance signoff is out of scope for this contract; this
> document is the engineering surface area we are committing to.

This is **software in support of a wellness recommendation service**, not a
diagnostic medical device. Even so, the data touched (factor scores,
condition risk labels) is sensitive personal health information, so we treat
it under SaMD (Software as a Medical Device) hygiene principles.

## What data we handle

- **Employee identifier** (`E0001` or `E_IBM_001` format, opaque, not a name).
- **Tenant id and name** (partner organisation like IBM, Microsoft).
- **Region + legacy tenant string** (geographic + organisational metadata).
- **Health records**: factor, chronic condition, status, severity, value,
  improvement rate, record date.
- **Generated recommendations**: product id, score, reasons, algorithm
  version, generated_at. Stored in the `recommendations` audit table
  (per-employee runs only; org-level runs are not currently audited).

No PII outside of an opaque employee id. No names, no contact details, no
free-text employee input.

## PIPEDA principles

PIPEDA's 10 fair-information principles, mapped to what this codebase does:

| # | Principle | Status | Where it lives |
|---|-----------|--------|----------------|
| 1 | Accountability | Planned | Will name a privacy lead in the deployed environment. Codebase logs every request with a request id for traceability. |
| 2 | Identifying purposes | Done | README + this doc state purpose: ranked wellness recommendations only. |
| 3 | Consent | Out of scope (Nytia handles) | Consent is captured upstream in Hinsight; we never collect data directly. |
| 4 | Limiting collection | Done | The API reads only the fields needed for scoring. No extra columns ingested. |
| 5 | Limiting use, disclosure, retention | Partial | Recommendations are written to an audit table indefinitely; retention policy TBD. **Action item:** add `retention_days` policy. |
| 6 | Accuracy | Done | The algorithm version is recorded with every recommendation row so we can re-score later if the rules change. |
| 7 | Safeguards | Partial | See "Security controls" below. |
| 8 | Openness | Done | Open documentation in this repo: README, this file, architecture.md. |
| 9 | Individual access | Planned | An employee-facing endpoint to retrieve their own recommendation history is on the roadmap (not built). |
| 10 | Challenging compliance | Planned | A documented process to raise privacy concerns. Owned by Nytia, not the engineering team. |

## HIPAA-style controls (engineering view)

These map directly to PIPEDA principle 7 (Safeguards). HIPAA terminology is
included because most engineering tooling is described in it.

### Access control

- **Authentication/Authorization**: not implemented yet. The API is currently
  open inside the local network. When deployed, will live behind Cloud Run
  IAM + a service-to-service token for callers.
- **Tenant isolation: currently fake.** This is the most important gap
  in this section.
  - The org-level routes take `tenant_id` from the URL path with no auth
    check (`GET /tenants/{id}/profile`,
    `GET /tenants/{id}/recommendations`).
  - Anyone with the URL can read any tenant's workforce data. That is OK
    for the demo and local dev and is flagged with a TODO comment at the
    top of `app/routers/organization.py`.
  - For HIPAA / PIPEDA compliance in production this must change to JWT
    authentication with a tenant claim. Every query that touches
    tenant-scoped tables (`employees`, `health_records`,
    `recommendations`) must filter by the authenticated tenant's id.
    Never trust the URL parameter alone. Cross-tenant data access is the
    single biggest privacy risk in this codebase.
  - This is the same control point that PIPEDA principle 7 (Safeguards)
    and HIPAA's access-control technical safeguard both require.
- **Database credentials**: never hardcoded. Loaded from environment via
  `pydantic-settings` (see `app/config.py`). The local `.env` is gitignored.
- **Container user**: the production image runs as a non-root user (`app`).

### Audit logging

- Every recommendation set is persisted to the `recommendations` table with
  `employee_id`, `product_id`, `score`, `reason`, `algorithm_version`,
  `generated_at`. Provides a record of what was suggested to whom and why.
- HTTP access log is one JSON line per request, includes `request_id`,
  `method`, `path`, `status_code`, `duration_ms` (see
  `app/main.py::RequestLoggingMiddleware`). The same request_id is echoed
  back to the client as an `x-request-id` header for correlation.
- Errors are logged with the same `request_id` so a failed call can be
  traced from client to server in one search.

### Transport and storage

- **In transit**: TLS terminated at the load balancer in production
  (Cloud Run does this automatically). Local dev is HTTP only.
- **At rest**: Cloud SQL has disk encryption enabled by default. Local
  Postgres uses the Docker volume without explicit encryption (acceptable
  for dev only).
- **Secrets**: planned to live in Google Secret Manager once cloud
  deployment lands. Today they come from environment variables.

### Input validation

- All request payloads are validated by Pydantic schemas in `app/schemas/`
  before they reach service code.
- Numeric query params (`top_n`) are bounded (1-50) in the router.
- Database CHECK constraints enforce enum values for factor / condition /
  status / severity / unit / service_type (see `app/models/`).
- Rate limiting (`slowapi`) protects the API: 30/min on `/recommend`, 120/min
  default elsewhere. 429 is the response.

### Error handling

- Centralised handlers in `app/exceptions.py` return a stable
  `{error: "<slug>", detail: ...}` JSON shape.
- Unhandled exceptions never leak stack traces to the client; they are
  logged server-side with the request id.

### ML-specific concerns

- The training data is **synthetic** (generated by
  `scripts/generate_training_data.py`). No real employee data is used to
  train the model.
- The model file is **gitignored**; it is built locally or in CI from the
  scripts. Provenance is the script source + the random seed.
- Predictions are advisory ("ML predicts elevated X risk") and the rule
  layer always remains the dominant scoring source.

## Open items

- [ ] **Tenant isolation: JWT auth + per-tenant query scoping.** Critical
  before any real tenant data lands. PIPEDA principle 7 / HIPAA access
  control. Currently the URL parameter is trusted.
- [ ] Retention policy for `recommendations` audit rows (PIPEDA principle 5).
- [ ] Authentication on the API in general (currently open).
- [ ] Self-serve recommendation history endpoint for employees (PIPEDA 9).
- [ ] Secret Manager integration once cloud deploy is wired up.
- [ ] Org-level audit log: today only per-employee runs are audited; if
  the HR dashboard becomes a billable surface we will want to log org
  recommendation runs too.
- [ ] Final privacy lead identified in the deployed environment.

## References

- PIPEDA Fair Information Principles: https://www.priv.gc.ca/en/privacy-topics/privacy-laws-in-canada/the-personal-information-protection-and-electronic-documents-act-pipeda/p_principle/
- Google Cloud HIPAA compliance: https://cloud.google.com/security/compliance/hipaa
