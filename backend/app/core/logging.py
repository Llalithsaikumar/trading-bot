"""
Structured logging setup using Loguru.
Outputs JSON in production, coloured text in development.
"""
from __future__ import annotations

import sys

from loguru import logger

from app.core.config import settings


def setup_logging() -> None:
    """Configure Loguru sinks based on application settings."""
    logger.remove()

    fmt_text = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "{message}"
    )
    fmt_json = (
        '{{"time":"{time:YYYY-MM-DD HH:mm:ss.SSS}",'
        '"level":"{level}",'
        '"name":"{name}",'
        '"function":"{function}",'
        '"line":{line},'
        '"message":"{message}"}}'
    )

    fmt = fmt_json if settings.LOG_FORMAT == "json" else fmt_text

    # Console sink
    logger.add(
        sys.stdout,
        format=fmt,
        level=settings.LOG_LEVEL,
        colorize=settings.LOG_FORMAT == "text",
        backtrace=settings.APP_DEBUG,
        diagnose=settings.APP_DEBUG,
    )

    # File sink (rotated)
    if settings.LOG_FILE_PATH:
        logger.add(
            settings.LOG_FILE_PATH,
            format=fmt_json,
            level=settings.LOG_LEVEL,
            rotation="10 MB",
            retention="30 days",
            compression="gz",
            enqueue=True,  # thread-safe async write
        )

    logger.info("Logging initialised", level=settings.LOG_LEVEL, format=settings.LOG_FORMAT)
