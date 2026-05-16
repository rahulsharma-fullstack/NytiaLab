"""Centralised exception handlers for the FastAPI app.

We translate internal service exceptions into clean JSON HTTP responses so
routers do not have to repeat the same try/except pattern.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.services import EmployeeNotFoundError, ProductNotFoundError

logger = logging.getLogger("nytia.errors")


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all error handlers to the given FastAPI app."""

    @app.exception_handler(EmployeeNotFoundError)
    async def employee_not_found(_request: Request, exc: EmployeeNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "employee_not_found", "detail": str(exc)},
        )

    @app.exception_handler(ProductNotFoundError)
    async def product_not_found(_request: Request, exc: ProductNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": "product_not_found", "detail": str(exc)},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": "http_error", "detail": exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": "validation_error", "detail": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unhandled exception",
            extra={"path": str(request.url.path), "method": request.method},
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "internal_server_error", "detail": "Something went wrong."},
        )
