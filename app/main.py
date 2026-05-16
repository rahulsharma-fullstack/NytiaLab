"""FastAPI application entry point."""

import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.exceptions import register_exception_handlers
from app.logging_config import configure_logging
from app.routers import employees, health, products, recommendations

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

register_exception_handlers(app)

app.include_router(health.router)
app.include_router(employees.router)
app.include_router(products.router)
app.include_router(recommendations.router)


@app.get("/")
def root() -> dict[str, str]:
    """Root endpoint. Returns basic API info."""
    return {
        "name": "Nytia Recommender API",
        "version": "0.1.0",
        "docs": "/docs",
        "demo": "/demo",
    }
