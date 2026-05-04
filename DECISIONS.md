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
