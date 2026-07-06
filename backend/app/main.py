"""
Application entry point.

Initialises FastAPI, registers routers, mounts middleware,
and wires up lifespan events (DB pool, Redis, Prometheus).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.exceptions import (
    AppError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    RiskLimitExceededError,
)
from app.core.logging import setup_logging


# ---------------------------------------------------------------------------
# Lifespan – startup / shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application lifecycle: open connections on startup, close on shutdown."""
    setup_logging()

    from loguru import logger  # noqa: PLC0415

    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("Starting {app_name} ({env})", app_name=settings.APP_NAME, env=settings.APP_ENV)

    from app.infrastructure.cache.redis_client import get_redis_client  # noqa: PLC0415

    await get_redis_client()
    logger.info("Redis ready")

    if settings.PROMETHEUS_ENABLED:
        try:
            from prometheus_fastapi_instrumentator import Instrumentator  # noqa: PLC0415

            Instrumentator().instrument(app).expose(app, endpoint="/metrics", tags=["Monitoring"])
            logger.info("Prometheus metrics exposed at /metrics")
        except ImportError:
            logger.warning("prometheus_fastapi_instrumentator not installed; skipping metrics")

    logger.info("Application startup complete")

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────────
    from app.infrastructure.cache.redis_client import close_redis  # noqa: PLC0415

    await close_redis()
    logger.info("Application shutdown complete")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------
def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description="Autonomous AI Crypto Trading Platform",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────────────────────────────
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from app.api.middleware.logging_middleware import LoggingMiddleware  # noqa: PLC0415

    application.add_middleware(LoggingMiddleware)

    # ── Exception handlers ───────────────────────────────────────────────────
    from app.api.middleware.exception_handler import (  # noqa: PLC0415
        app_error_handler,
        auth_error_handler,
        forbidden_handler,
        not_found_handler,
        risk_limit_handler,
    )

    application.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    application.add_exception_handler(NotFoundError, not_found_handler)  # type: ignore[arg-type]
    application.add_exception_handler(AuthenticationError, auth_error_handler)  # type: ignore[arg-type]
    application.add_exception_handler(AuthorizationError, forbidden_handler)  # type: ignore[arg-type]
    application.add_exception_handler(RiskLimitExceededError, risk_limit_handler)  # type: ignore[arg-type]

    # ── Routers ──────────────────────────────────────────────────────────────
    from app.api.v1 import api_router  # noqa: PLC0415

    application.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return application


app = create_app()


# ---------------------------------------------------------------------------
# Health probes (unauthenticated, used by Docker / k8s)
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Health"], summary="Liveness probe")
async def health_liveness() -> dict[str, str]:
    """Returns 200 if the process is running."""
    return {"status": "ok"}


@app.get("/health/ready", tags=["Health"], summary="Readiness probe")
async def health_readiness() -> dict[str, object]:
    """
    Returns 200 only when all dependencies (DB, Redis) are reachable.
    Returns 503 with details if any dependency is down.
    """
    import asyncio  # noqa: PLC0415

    from fastapi import HTTPException  # noqa: PLC0415
    from fastapi.responses import JSONResponse  # noqa: PLC0415

    checks: dict[str, str] = {}
    healthy = True

    # ── Redis ────────────────────────────────────────────────────────────────
    try:
        from app.infrastructure.cache.redis_client import get_redis_client  # noqa: PLC0415

        redis = await get_redis_client()
        await asyncio.wait_for(redis.ping(), timeout=2.0)
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"
        healthy = False

    # ── Database ─────────────────────────────────────────────────────────────
    try:
        from sqlalchemy import text  # noqa: PLC0415

        from app.infrastructure.database.session import engine  # noqa: PLC0415

        async with engine.connect() as conn:
            await asyncio.wait_for(conn.execute(text("SELECT 1")), timeout=2.0)
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"
        healthy = False

    body = {"status": "ok" if healthy else "degraded", "checks": checks}
    if not healthy:
        return JSONResponse(status_code=503, content=body)
    return body
