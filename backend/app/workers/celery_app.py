"""
Celery application factory.
Queues: default, trading, market_data, notifications
"""

from __future__ import annotations

from celery import Celery

from app.core.config import settings

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
celery_app = Celery(
    "crypto_trader",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.tasks.trading_tasks",
        "app.workers.tasks.market_data_tasks",
        "app.workers.tasks.notification_tasks",
    ],
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,  # only ack after successful completion
    worker_prefetch_multiplier=1,  # fair scheduling
    task_routes={
        "app.workers.tasks.trading_tasks.*": {"queue": "trading"},
        "app.workers.tasks.market_data_tasks.*": {"queue": "market_data"},
        "app.workers.tasks.notification_tasks.*": {"queue": "notifications"},
    },
    # RedBeat periodic tasks
    redbeat_redis_url=settings.CELERY_BROKER_URL,
)

# ---------------------------------------------------------------------------
# Periodic schedule (Beat)
# ---------------------------------------------------------------------------
celery_app.conf.beat_schedule = {
    "sync-market-data-every-minute": {
        "task": "app.workers.tasks.market_data_tasks.sync_market_data",
        "schedule": 60.0,  # every 60 seconds
    },
    "run-active-strategies-every-5-minutes": {
        "task": "app.workers.tasks.trading_tasks.run_active_strategies",
        "schedule": 300.0,  # every 5 minutes
    },
    "check-alerts-every-minute": {
        "task": "app.workers.tasks.notification_tasks.check_price_alerts",
        "schedule": 60.0,
    },
    "sync-order-statuses-every-30-seconds": {
        "task": "app.workers.tasks.trading_tasks.sync_order_statuses",
        "schedule": 30.0,
    },
}
