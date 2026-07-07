"""
PolymarketService — fetch, cache, and serve prediction market data.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.logging import logger
from app.domain.models.polymarket import PolymarketSnapshot
from app.domain.schemas.polymarket import PolymarketMarketResponse, PolymarketSummaryResponse
from app.infrastructure.cache.redis_client import cache_get, cache_set
from app.infrastructure.repositories.polymarket_repository import PolymarketRepository


class PolymarketService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = PolymarketRepository(session)

    async def fetch_crypto_markets(self, limit: int = 50) -> list[PolymarketMarketResponse]:
        """Fetch active crypto prediction markets from Polymarket Gamma API."""
        if not settings.POLYMARKET_ENABLED:
            logger.warning("Polymarket integration is disabled in configuration")
            return []

        # Check Cache first
        cache_key = "polymarket:crypto_markets"
        cached = await cache_get(cache_key)
        if cached:
            try:
                data = json.loads(cached)
                return [
                    PolymarketMarketResponse(
                        condition_id=item["condition_id"],
                        question=item["question"],
                        description=item.get("description"),
                        outcome_yes_price=Decimal(str(item["outcome_yes_price"])),
                        outcome_no_price=Decimal(str(item["outcome_no_price"])),
                        probability=float(item["probability"]),
                        liquidity=Decimal(str(item["liquidity"])),
                        volume=Decimal(str(item["volume"])),
                        volume_24h=Decimal(str(item["volume_24h"])),
                        end_date=datetime.fromisoformat(item["end_date"]) if item.get("end_date") else None,
                        category=item.get("category"),
                        active=bool(item["active"]),
                        fetched_at=datetime.fromisoformat(item["fetched_at"])
                    )
                    for item in data
                ]
            except Exception as e:
                logger.error("Failed to parse cached Polymarket data", error=str(e))

        # Fetch from Gamma API
        api_url = f"{settings.POLYMARKET_API_URL}/markets?active=true&limit=100"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(api_url, timeout=10.0)
                response.raise_for_status()
                markets = response.json()
        except Exception as e:
            logger.error("Failed to fetch markets from Polymarket API", error=str(e))
            # Fallback to DB
            db_snapshots = await self._repository.get_latest_snapshots(limit=limit)
            return [self._map_model_to_response(db_snap) for db_snap in db_snapshots]

        # Filter and extract
        import re
        keywords_pattern = re.compile(
            r"\b(bitcoin|btc|ethereum|eth|crypto|cryptocurrency|solana|sol|xrp|cardano|ada|defi|nft|web3|blockchain)\b",
            re.IGNORECASE
        )

        fetched_at = datetime.now(UTC)
        filtered_markets = []

        for m in markets:
            if not isinstance(m, dict):
                continue
            question = m.get("question") or m.get("title") or ""
            description = m.get("description") or ""
            category = m.get("category") or ""
            
            is_crypto = (
                bool(keywords_pattern.search(question)) or
                bool(keywords_pattern.search(description)) or
                bool(keywords_pattern.search(category))
            )
            if not is_crypto:
                continue

            condition_id = m.get("conditionId") or m.get("id")
            if not condition_id:
                continue

            # Extract prices
            outcome_prices = m.get("outcomePrices")
            yes_price = Decimal("0.5")
            no_price = Decimal("0.5")
            if outcome_prices:
                try:
                    if isinstance(outcome_prices, list) and len(outcome_prices) >= 2:
                        yes_price = Decimal(str(outcome_prices[0]))
                        no_price = Decimal(str(outcome_prices[1]))
                    elif isinstance(outcome_prices, str):
                        prices_list = json.loads(outcome_prices)
                        if len(prices_list) >= 2:
                            yes_price = Decimal(str(prices_list[0]))
                            no_price = Decimal(str(prices_list[1]))
                except Exception:
                    pass

            liquidity = Decimal(str(m.get("liquidity") or m.get("liquidityUsd") or 0))
            volume = Decimal(str(m.get("volume") or m.get("volumeUsd") or 0))
            volume_24h = Decimal(str(m.get("volume24h") or m.get("volume24hUsd") or 0))

            end_date = None
            end_date_raw = m.get("endDate") or m.get("endDateIso")
            if end_date_raw:
                try:
                    import arrow
                    end_date = arrow.get(end_date_raw).datetime
                except Exception:
                    pass

            active = m.get("active", True)
            if isinstance(active, str):
                active = active.lower() == "true"

            # Create snapshot
            snapshot = PolymarketSnapshot(
                condition_id=str(condition_id),
                question=str(question),
                description=str(description) if description else None,
                outcome_yes_price=yes_price,
                outcome_no_price=no_price,
                liquidity=liquidity,
                volume=volume,
                volume_24h=volume_24h,
                end_date=end_date,
                category=str(category) if category else "Crypto",
                active=bool(active),
                fetched_at=fetched_at
            )
            self._session.add(snapshot)
            
            prob = float(yes_price)
            
            response_item = PolymarketMarketResponse(
                condition_id=str(condition_id),
                question=str(question),
                description=str(description) if description else None,
                outcome_yes_price=yes_price,
                outcome_no_price=no_price,
                probability=prob,
                liquidity=liquidity,
                volume=volume,
                volume_24h=volume_24h,
                end_date=end_date,
                category=str(category) if category else "Crypto",
                active=bool(active),
                fetched_at=fetched_at
            )
            filtered_markets.append(response_item)

        await self._session.flush()

        # Cache response
        if filtered_markets:
            cache_data = [
                {
                    "condition_id": item.condition_id,
                    "question": item.question,
                    "description": item.description,
                    "outcome_yes_price": str(item.outcome_yes_price),
                    "outcome_no_price": str(item.outcome_no_price),
                    "probability": item.probability,
                    "liquidity": str(item.liquidity),
                    "volume": str(item.volume),
                    "volume_24h": str(item.volume_24h),
                    "end_date": item.end_date.isoformat() if item.end_date else None,
                    "category": item.category,
                    "active": item.active,
                    "fetched_at": item.fetched_at.isoformat()
                }
                for item in filtered_markets
            ]
            await cache_set(cache_key, json.dumps(cache_data), ttl=settings.POLYMARKET_CACHE_TTL)

        return filtered_markets[:limit]

    async def get_latest_insights(self, limit: int = 50) -> list[PolymarketMarketResponse]:
        """Fetch latest market snapshots stored in DB."""
        db_snapshots = await self._repository.get_latest_snapshots(limit=limit)
        return [self._map_model_to_response(db_snap) for db_snap in db_snapshots]

    async def get_market_by_condition_id(self, condition_id: str, limit: int = 20) -> list[PolymarketMarketResponse]:
        """Fetch historical snapshots of a specific market."""
        db_snapshots = await self._repository.get_by_condition_id(condition_id, limit=limit)
        return [self._map_model_to_response(db_snap) for db_snap in db_snapshots]

    async def get_summary(self) -> PolymarketSummaryResponse:
        """Get summarized intelligence stats for prediction markets."""
        markets = await self.get_latest_insights()
        if not markets:
            return PolymarketSummaryResponse(
                total_markets=0,
                avg_probability=0.5,
                total_liquidity=Decimal("0"),
                markets=[]
            )

        total_markets = len(markets)
        total_liquidity = sum(m.liquidity for m in markets)
        avg_probability = sum(m.probability for m in markets) / total_markets

        return PolymarketSummaryResponse(
            total_markets=total_markets,
            avg_probability=avg_probability,
            total_liquidity=total_liquidity,
            markets=markets
        )

    def _map_model_to_response(self, model: PolymarketSnapshot) -> PolymarketMarketResponse:
        return PolymarketMarketResponse(
            condition_id=model.condition_id,
            question=model.question,
            description=model.description,
            outcome_yes_price=model.outcome_yes_price,
            outcome_no_price=model.outcome_no_price,
            probability=float(model.outcome_yes_price),
            liquidity=model.liquidity,
            volume=model.volume,
            volume_24h=model.volume_24h,
            end_date=model.end_date,
            category=model.category,
            active=model.active,
            fetched_at=model.fetched_at
        )
