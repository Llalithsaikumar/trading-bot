"""
Seed the database with development fixtures.

Usage:
    uv run python -m scripts.seed_db

Creates:
  - Admin user  (admin@cryptotrader.dev / admin1234)
  - Demo user   (demo@cryptotrader.dev / demo1234)
  - Paper-trading portfolio for the demo user
  - Sample BTC/ETH momentum strategy
"""

from __future__ import annotations

import asyncio
import sys
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ── Bootstrap path so the script can be run from the backend/ dir ──────────
import os

# Ensure backend/ is on sys.path when invoked via `python -m scripts.seed_db`
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.config import settings
from app.core.security import hash_password
from app.domain.enums.user import UserRole, UserStatus
from app.domain.enums.trading import StrategyStatus, TimeFrame
from app.domain.models.user import User
from app.domain.models.portfolio import Portfolio
from app.domain.models.strategy import Strategy

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ADMIN = {
    "email": "admin@cryptotrader.dev",
    "username": "admin",
    "full_name": "Admin User",
    "password": "admin1234",
    "role": UserRole.ADMIN,
    "status": UserStatus.ACTIVE,
    "is_active": True,
    "is_email_verified": True,
}

DEMO = {
    "email": "demo@cryptotrader.dev",
    "username": "demo",
    "full_name": "Demo Trader",
    "password": "demo1234",
    "role": UserRole.TRADER,
    "status": UserStatus.ACTIVE,
    "is_active": True,
    "is_email_verified": True,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(data: dict) -> User:
    return User(
        email=data["email"],
        username=data["username"],
        full_name=data["full_name"],
        hashed_password=hash_password(data["password"]),
        role=data["role"],
        status=data["status"],
        is_active=data["is_active"],
        is_email_verified=data["is_email_verified"],
    )


async def _get_or_create_user(session: AsyncSession, data: dict) -> tuple[User, bool]:
    result = await session.execute(select(User).where(User.email == data["email"]))
    user = result.scalar_one_or_none()
    if user:
        return user, False
    user = _make_user(data)
    session.add(user)
    await session.flush()
    return user, True


async def seed(session: AsyncSession) -> None:
    print("-" * 60)
    print("  CryptoTrader AI  -  Database Seed")
    print("-" * 60)

    # -- Users ----------------------------------------------------------------
    admin, created = await _get_or_create_user(session, ADMIN)
    print(f"{'Created' if created else 'Exists '} admin  -> {admin.email}")

    demo, created = await _get_or_create_user(session, DEMO)
    print(f"{'Created' if created else 'Exists '} demo   -> {demo.email}")

    # -- Portfolio ------------------------------------------------------------
    result = await session.execute(
        select(Portfolio).where(
            Portfolio.user_id == demo.id,
            Portfolio.name == "Paper Portfolio",
        )
    )
    portfolio = result.scalar_one_or_none()
    if portfolio:
        print("Exists  portfolio -> Paper Portfolio")
    else:
        portfolio = Portfolio(
            user_id=demo.id,
            name="Paper Portfolio",
            exchange="binance",
            quote_currency="USDT",
            initial_balance=Decimal("10000"),
            total_value_usdt=Decimal("10000"),
            available_balance=Decimal("10000"),
            unrealized_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
            daily_pnl=Decimal("0"),
            is_paper_trading=True,
        )
        session.add(portfolio)
        await session.flush()
        print("Created portfolio -> Paper Portfolio  ($10,000 USDT)")

    # -- Strategy -------------------------------------------------------------
    result = await session.execute(
        select(Strategy).where(
            Strategy.user_id == demo.id,
            Strategy.name == "BTC/ETH Momentum",
        )
    )
    strategy = result.scalar_one_or_none()
    if strategy:
        print("Exists  strategy  -> BTC/ETH Momentum")
    else:
        strategy = Strategy(
            user_id=demo.id,
            name="BTC/ETH Momentum",
            description="Trend-following strategy on BTC and ETH using RSI + MACD signals.",
            exchange="binance",
            symbols=["BTCUSDT", "ETHUSDT"],
            timeframe=TimeFrame.H1,
            status=StrategyStatus.PAUSED,
            max_position_size_pct=Decimal("5.0"),
            stop_loss_pct=Decimal("2.0"),
            take_profit_pct=Decimal("4.0"),
            max_open_positions=2,
            config={
                "indicators": ["rsi", "macd", "bb"],
                "rsi_period": 14,
                "macd_fast": 12,
                "macd_slow": 26,
                "macd_signal": 9,
            },
        )
        session.add(strategy)
        await session.flush()
        print("Created strategy  -> BTC/ETH Momentum")

    await session.commit()

    print("-" * 60)
    print("  Seed complete!")
    print()
    print("  Login credentials:")
    print(f"    Admin  ->  {ADMIN['email']}  /  {ADMIN['password']}")
    print(f"    Demo   ->  {DEMO['email']}   /  {DEMO['password']}")
    print("-" * 60)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        await seed(session)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
