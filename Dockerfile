# Multi-stage production image for the Nytia Recommender API.
#
# Stage 1 (builder): uv-managed virtualenv with the locked dependencies.
# Stage 2 (runtime): slim base, non-root user, only the venv + app code.
#
# Image size target: < 350 MB. ML deps (numpy, scipy, scikit-learn) are
# the dominant cost.

# ---------- Stage 1: builder ----------
FROM python:3.12-slim AS builder

# uv installs into /root/.local/bin by default
ENV UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv

# Copy uv from the official image (single binary, no apt needed)
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /usr/local/bin/

WORKDIR /app

# Install only the locked main deps first so this layer is cached when
# only the source code changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Now bring in the source and finish installing the project itself.
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY scripts/ ./scripts/
RUN uv sync --frozen --no-dev


# ---------- Stage 2: runtime ----------
FROM python:3.12-slim AS runtime

# libpq is needed at runtime for psycopg2. Everything else stays in the venv.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# Run as a non-root user.
RUN groupadd --system app && useradd --system --gid app --home /app app

WORKDIR /app

# Copy the prebuilt virtualenv and the application from the builder.
COPY --from=builder --chown=app:app /opt/venv /opt/venv
COPY --from=builder --chown=app:app /app /app

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

USER app

EXPOSE 8000

# Cloud Run and most load balancers hit /health for liveness.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:${PORT}/health || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
