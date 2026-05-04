# Nytia Recommender


Wellness service recommendation engine for Nytia Labs.

## Overview

A REST API that recommends wellness services to employees based on their
health profile (contributing factors and chronic conditions). Combines
rules-based matching with ML-predicted risk to surface relevant preventive
and treatment services.

## Tech Stack

- **Language:** Python 3.12
- **Framework:** FastAPI
- **Database:** PostgreSQL (via SQLAlchemy + Alembic)
- **ML:** scikit-learn
- **Package manager:** uv
- **Deployment target:** Google Cloud Run

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Docker Desktop (for local Postgres, added later)
- Git

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/nytia-recommender.git
cd nytia-recommender
```

### 2. Install dependencies

```bash
uv sync
```

This creates a virtual environment and installs all dependencies from `uv.lock`.

### 3. Run the API

```bash
uv run uvicorn app.main:app --reload --port 8000
```

The API is now running at http://localhost:8000

### 4. Explore

- **API root:** http://localhost:8000/
- **Health check:** http://localhost:8000/health
- **Interactive docs:** http://localhost:8000/docs

## Project Structure
