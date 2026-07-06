"""
Global exception handlers — map domain exceptions to HTTP responses.
Register these in app/main.py via app.add_exception_handler().
"""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    AppError,
    AuthenticationError,
    AuthorizationError,
    InsufficientBalanceError,
    NotFoundError,
    RiskLimitExceededError,
)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"error": exc.message, "code": exc.code},
    )


async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"error": exc.message, "code": exc.code},
    )


async def auth_error_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={"error": exc.message, "code": exc.code},
    )


async def forbidden_handler(request: Request, exc: AuthorizationError) -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content={"error": exc.message, "code": exc.code},
    )


async def risk_limit_handler(
    request: Request, exc: RiskLimitExceededError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": exc.message, "code": exc.code},
    )
