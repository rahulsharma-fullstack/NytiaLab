"""FastAPI application entry point."""

import logging
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.exceptions import register_exception_handlers
from app.logging_config import configure_logging
from app.rate_limit import install_rate_limiter
from app.routers import employees, health, organization, products, recommendations

STATIC_DIR = Path(__file__).parent / "static"

configure_logging()

access_logger = logging.getLogger("nytia.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request as a single JSON line with a request id and duration."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            access_logger.exception(
                "request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                },
            )
            raise
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        access_logger.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        response.headers["x-request-id"] = request_id
        return response


app = FastAPI(
    title="Nytia Recommender API",
    description="Wellness service recommendation engine for Nytia Labs.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

install_rate_limiter(app)

register_exception_handlers(app)

app.include_router(health.router)
app.include_router(employees.router)
app.include_router(products.router)
app.include_router(recommendations.router)
app.include_router(organization.router)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    """Root endpoint. Returns basic API info and the demo URLs."""
    return {
        "name": "Nytia Recommender API",
        "version": "0.1.0",
        "docs": "/docs",
        "demo": "/demo",
        "demo_org": "/demo/org",
    }


@app.get("/demo", include_in_schema=False)
def demo_page() -> FileResponse:
    """Serve the per-employee demo single-page UI."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/demo/org", include_in_schema=False)
def demo_org_page() -> FileResponse:
    """Serve the org-level (tenant) demo single-page UI."""
    return FileResponse(STATIC_DIR / "org.html")
