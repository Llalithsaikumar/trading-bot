"""Notification and alert tasks."""
from __future__ import annotations

from celery import shared_task


import asyncio
from celery import shared_task
from loguru import logger


def _run(coro):
    """Run an async coroutine from a synchronous Celery worker."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _check_price_alerts_async() -> dict:
    import json
    from decimal import Decimal

    from sqlalchemy import select

    from app.core.config import settings
    from app.domain.models.alert import Alert
    from app.infrastructure.cache.redis_client import cache_get
    from app.infrastructure.database.session import AsyncSessionLocal

    triggered_count = 0
    async with AsyncSessionLocal() as session:
        stmt = select(Alert).where(Alert.is_active.is_(True), Alert.is_triggered.is_(False))
        result = await session.execute(stmt)
        alerts = result.scalars().all()

        prices = {}

        for alert in alerts:
            symbol = alert.symbol
            if symbol not in prices:
                cached = await cache_get(f"ticker:{settings.EXCHANGE_DEFAULT}:{symbol}")
                if cached:
                    try:
                        data = json.loads(cached)
                        prices[symbol] = Decimal(str(data["last"]))
                    except Exception:
                        pass

            price = prices.get(symbol)
            if price is None:
                continue

            triggered = False
            if alert.alert_type == "price_above" and price >= alert.condition_value:
                triggered = True
            elif alert.alert_type == "price_below" and price <= alert.condition_value:
                triggered = True

            if triggered:
                alert.is_triggered = True
                alert.is_active = False
                session.add(alert)
                triggered_count += 1

                subject = f"Price Alert Triggered: {symbol}"
                body = f"The price of {symbol} has reached {price:.2f} USDT (alert set at {alert.alert_type} {alert.condition_value:.2f} USDT)."
                send_email_notification.delay(str(alert.user_id), subject, body)

        await session.commit()
    return {"triggered": triggered_count}


@shared_task(bind=True, name="app.workers.tasks.notification_tasks.check_price_alerts")
def check_price_alerts(self) -> dict:
    """Evaluate all active price alerts against current market prices."""
    try:
        return _run(_check_price_alerts_async())
    except Exception as exc:
        logger.error("check_price_alerts failed", error=str(exc))
        raise self.retry(exc=exc)


@shared_task(name="app.workers.tasks.notification_tasks.send_email_notification")
def send_email_notification(user_id: str, subject: str, body: str) -> None:
    """Send an email notification to a user."""
    import smtplib
    from email.mime.text import MIMEText
    import uuid

    from sqlalchemy import select

    from app.domain.models.user import User
    from app.infrastructure.database.session import AsyncSessionLocal

    async def get_user_email() -> str:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.id == uuid.UUID(user_id)))
            user = result.scalar_one_or_none()
            return user.email if user else "mock-user@example.com"

    try:
        email_addr = _run(get_user_email())
    except Exception:
        email_addr = "mock-user@example.com"

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = "alerts@cryptotrader.ai"
    msg["To"] = email_addr

    try:
        # Mailhog is running on localhost:1025 in dev compose
        with smtplib.SMTP("localhost", 1025) as server:
            server.send_message(msg)
        logger.info(f"Email notification sent to {email_addr}: {subject}")
    except Exception as e:
        logger.warning(f"Failed to send email to {email_addr} via Mailhog: {e}. Message: {subject}")

