"""FastAPI application entry point."""

from fastapi import FastAPI

from app.routers import health

app = FastAPI(
    title="Nytia Recommender API",
    description="Wellness service recommendation engine for Nytia Labs.",
    version="0.1.0",
)

# Register routers
app.include_router(health.router)


@app.get("/")
def root() -> dict[str, str]:
    """Root endpoint. Returns basic API info."""
    return {
        "name": "Nytia Recommender API",
        "version": "0.1.0",
        "docs": "/docs",
    }