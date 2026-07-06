"""
Celery tasks for paper trading background operations.

  sync_limit_orders    — check open limit/stop orders every ~10 s, fill triggered ones
  sync_position_prices — refresh position prices every ~30 s for live PnL dashboard
  reset_daily_pnl      — zero out daily_pnl on all portfolios at UTC midnight
"""

from __future__ import annotations

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


async def _sync_limit_orders_async() -> dict:
    from decimal import Decimal

    from sqlalchemy import select

    from app.domain.models.portfolio import Portfolio
    from app.infrastructure.database.session import AsyncSessionLocal
    from app.services.paper_trading.engine import PaperTradingEngine

    filled_total = 0
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Portfolio).where(Portfolio.is_paper_trading.is_(True))
        )
        for portfolio in result.scalars().all():
            try:
                engine = PaperTradingEngine(session)
                filled = await engine.process_pending_orders(portfolio)
                filled_total += len(filled)
                if filled:
                    logger.info(
                        "Limit orders filled",
                        portfolio_id=str(portfolio.id),
                        count=len(filled),
                    )
                await session.commit()
            except Exception as exc:
                await session.rollback()
                logger.error("Pending orders error", portfolio_id=str(portfolio.id), error=str(exc))
    return {"filled": filled_total}


async def _sync_position_prices_async() -> dict:
    from sqlalchemy import select

    from app.domain.models.portfolio import Portfolio
    from app.infrastructure.database.session import AsyncSessionLocal
    from app.services.paper_trading.engine import PaperTradingEngine

    updated = 0
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Portfolio).where(Portfolio.is_paper_trading.is_(True))
        )
        for portfolio in result.scalars().all():
            try:
                engine = PaperTradingEngine(session)
                await engine.sync_positions(portfolio)
                await session.commit()
                updated += 1
            except Exception as exc:
                await session.rollback()
                logger.warning(
                    "Position sync failed", portfolio_id=str(portfolio.id), error=str(exc)
                )
    return {"updated": updated}


async def _reset_daily_pnl_async() -> dict:
    from decimal import Decimal

    from sqlalchemy import update

    from app.domain.models.portfolio import Portfolio
    from app.infrastructure.database.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        await session.execute(
            update(Portfolio)
            .where(Portfolio.is_paper_trading.is_(True))
            .values(daily_pnl=Decimal("0"))
        )
        await session.commit()
    logger.info("Daily PnL reset complete")
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Public Celery tasks
# ---------------------------------------------------------------------------


@shared_task(
    bind=True,
    name="app.workers.tasks.trading_tasks.sync_limit_orders",
    max_retries=3,
    default_retry_delay=5,
)
def sync_limit_orders(self) -> dict:
    """Fill limit/stop orders whose price condition is now met. Run every ~10 s."""
    try:
        return _run(_sync_limit_orders_async())
    except Exception as exc:
        logger.error("sync_limit_orders failed", error=str(exc))
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    name="app.workers.tasks.trading_tasks.sync_position_prices",
    max_retries=3,
    default_retry_delay=10,
)
def sync_position_prices(self) -> dict:
    """Refresh live prices on all open positions and write equity snapshots. Run every ~30 s."""
    try:
        return _run(_sync_position_prices_async())
    except Exception as exc:
        logger.error("sync_position_prices failed", error=str(exc))
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    name="app.workers.tasks.trading_tasks.reset_daily_pnl",
    max_retries=2,
)
def reset_daily_pnl(self) -> dict:
    """Zero daily_pnl on all paper portfolios. Schedule at UTC midnight."""
    try:
        return _run(_reset_daily_pnl_async())
    except Exception as exc:
        raise self.retry(exc=exc)


async def _run_active_strategies_async() -> dict:
    from sqlalchemy import select

    from app.domain.enums.trading import StrategyStatus
    from app.domain.models.strategy import Strategy
    from app.infrastructure.database.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        stmt = select(Strategy).where(Strategy.status == StrategyStatus.ACTIVE)
        result = await session.execute(stmt)
        strategies = result.scalars().all()
        for s in strategies:
            run_strategy_task.delay(str(s.id))
    return {"triggered": len(strategies)}


async def _run_strategy_task_async(strategy_id: str) -> dict:
    import uuid
    from datetime import UTC, datetime
    from decimal import Decimal
    from langchain_anthropic import ChatAnthropic
    from langchain_openai import ChatOpenAI

    from app.agents.graph.builder import build_trading_graph
    from app.agents.graph.state import TradingState
    from app.agents.interfaces.base import AgentDependencies
    from app.core.config import settings
    from app.domain.models.portfolio import Portfolio
    from app.domain.models.strategy import Strategy, StrategyExecution
    from app.infrastructure.cache.redis_client import get_redis_client
    from app.infrastructure.database.session import AsyncSessionLocal
    from app.infrastructure.exchange import get_exchange
    from app.infrastructure.repositories.portfolio_repository import PortfolioRepository

    async with AsyncSessionLocal() as session:
        strategy = await session.get(Strategy, uuid.UUID(strategy_id))
        if strategy is None:
            logger.error(f"Strategy {strategy_id} not found")
            return {"status": "error", "error": "Strategy not found"}

        portfolio_repo = PortfolioRepository(session)
        portfolios = await portfolio_repo.get_paper_portfolios(strategy.user_id)
        portfolio = next((p for p in portfolios if p.exchange == strategy.exchange), None)
        if not portfolio:
            portfolio = Portfolio(
                user_id=strategy.user_id,
                name=f"Paper {strategy.exchange.capitalize()}",
                exchange=strategy.exchange,
                quote_currency="USDT",
                initial_balance=Decimal("100000"),
                total_value_usdt=Decimal("100000"),
                available_balance=Decimal("100000"),
                is_paper_trading=True,
            )
            session.add(portfolio)
            await session.flush()

        redis = await get_redis_client()
        exchange_client = get_exchange(strategy.exchange)

        llm = None
        if settings.ANTHROPIC_API_KEY:
            llm = ChatAnthropic(
                model=settings.LLM_MODEL,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                api_key=settings.ANTHROPIC_API_KEY,
            )
        elif settings.OPENAI_API_KEY:
            llm = ChatOpenAI(
                model="gpt-4o",
                temperature=settings.LLM_TEMPERATURE,
                api_key=settings.OPENAI_API_KEY,
            )

        deps = AgentDependencies(
            session=session,
            redis=redis,
            exchange=exchange_client,
            llm=llm,
        )

        initial_state = TradingState(
            strategy_id=str(strategy.id),
            exchange=strategy.exchange,
            symbols=strategy.symbols,
            timeframe=strategy.timeframe,
            portfolio_id=str(portfolio.id),
        )

        graph = build_trading_graph(deps)
        start_time = datetime.now(UTC)

        try:
            result_state = await graph.ainvoke(initial_state)
            duration_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)

            execution = StrategyExecution(
                strategy_id=strategy.id,
                run_id=result_state.get("run_id", str(uuid.uuid4())),
                status="success",
                signal=str(result_state.get("signal")),
                reasoning=result_state.get("reasoning"),
                tokens_used=0,
                duration_ms=duration_ms,
                error_message=None,
            )
            session.add(execution)
            await session.commit()

            return {
                "status": "success",
                "strategy_id": strategy_id,
                "signal": str(result_state.get("signal")),
                "order_placed": result_state.get("order_placed", False),
            }
        except Exception as e:
            duration_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
            logger.error(f"Strategy execution failed: {e}")
            execution = StrategyExecution(
                strategy_id=strategy.id,
                run_id=initial_state.run_id,
                status="failed",
                duration_ms=duration_ms,
                error_message=str(e),
            )
            session.add(execution)
            await session.commit()
            return {"status": "failed", "strategy_id": strategy_id, "error": str(e)}


@shared_task(
    bind=True,
    name="app.workers.tasks.trading_tasks.run_active_strategies",
    max_retries=3,
)
def run_active_strategies(self) -> dict:
    """trigger LangGraph agent runs for all active strategies."""
    try:
        return _run(_run_active_strategies_async())
    except Exception as exc:
        logger.error("run_active_strategies failed", error=str(exc))
        raise self.retry(exc=exc)


@shared_task(bind=True, name="app.workers.tasks.trading_tasks.run_strategy", max_retries=2)
def run_strategy_task(self, strategy_id: str) -> dict:
    """execute LangGraph trading agent for a single strategy."""
    try:
        return _run(_run_strategy_task_async(strategy_id))
    except Exception as exc:
        logger.error("run_strategy_task failed", error=str(exc))
        raise self.retry(exc=exc)


async def _reflect_on_completed_trade_async(order_id: str, realized_pnl: float) -> dict:
    import uuid
    from decimal import Decimal
    from langchain_anthropic import ChatAnthropic
    from langchain_openai import ChatOpenAI

    from app.infrastructure.database.session import AsyncSessionLocal
    from app.infrastructure.cache.redis_client import get_redis_client
    from app.agents.interfaces.base import AgentDependencies
    from app.agents.nodes.trade_reflection_node import TradeReflectionAgent
    from app.core.config import settings

    async with AsyncSessionLocal() as session:
        redis = await get_redis_client()

        llm = None
        if settings.ANTHROPIC_API_KEY:
            llm = ChatAnthropic(
                model=settings.LLM_MODEL,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                api_key=settings.ANTHROPIC_API_KEY,
            )
        elif settings.OPENAI_API_KEY:
            llm = ChatOpenAI(
                model="gpt-4o",
                temperature=settings.LLM_TEMPERATURE,
                api_key=settings.OPENAI_API_KEY,
            )

        deps = AgentDependencies(session=session, redis=redis, llm=llm)

        agent = TradeReflectionAgent(deps)
        result = await agent.reflect_on_trade(uuid.UUID(order_id), Decimal(str(realized_pnl)))
        await session.commit()

        return result or {"status": "skipped"}


@shared_task(
    bind=True,
    name="app.workers.tasks.trading_tasks.reflect_on_completed_trade",
    max_retries=2,
)
def reflect_on_completed_trade(self, order_id: str, realized_pnl: float) -> dict:
    """Analyze completed trade and store lessons in long-term memory."""
    try:
        return _run(_reflect_on_completed_trade_async(order_id, realized_pnl))
    except Exception as exc:
        logger.error("reflect_on_completed_trade failed", error=str(exc))
        raise self.retry(exc=exc)
