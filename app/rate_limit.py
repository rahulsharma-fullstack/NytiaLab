"""Rate limiting for the API.

Uses slowapi (a starlette-compatible wrapper around limits). The limiter is
keyed by client IP. Per-route limits are applied with the
`@limiter.limit("...")` decorator on the router function.

Hot endpoints (the recommender, which can be expensive) get a tighter limit;
other routes use a softer default.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

logger = logging.getLogger("nytia.ratelimit")

# Soft default applied to every route unless overridden.
DEFAULT_LIMIT = "120/minute"

# Tighter limit for the recommender, which does the heavy work.
RECOMMEND_LIMIT = "30/minute"

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[DEFAULT_LIMIT],
)


def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Return a clean JSON 429 instead of slowapi's default text response."""
    logger.warning(
        "rate limit exceeded",
        extra={
            "path": request.url.path,
            "client": get_remote_address(request),
            "detail": str(exc.detail),
        },
    )
    response = JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"error": "rate_limit_exceeded", "detail": str(exc.detail)},
    )
    # slowapi expects standard rate-limit headers to be present on the response.
    response = request.app.state.limiter._inject_headers(response, request.state.view_rate_limit)
    return response


def install_rate_limiter(app: FastAPI) -> None:
    """Wire the limiter, middleware, and 429 handler into the app."""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
