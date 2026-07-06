"""
Request / response logging middleware.
Logs structured JSON: method, path, status, duration, request_id.
"""
from __future__ import annotations

import time
import uuid

from fastapi import Request, Response
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        request_id = str(uuid.uuid4())
        start = time.perf_counter()

        with logger.contextualize(request_id=request_id):
            logger.info(
                "Incoming request",
                method=request.method,
                path=request.url.path,
                query=str(request.query_params),
            )
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info(
                "Request completed",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration_ms=duration_ms,
            )

        response.headers["X-Request-ID"] = request_id
        return response
