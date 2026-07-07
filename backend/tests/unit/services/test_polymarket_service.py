import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from datetime import UTC, datetime

from app.services.polymarket.polymarket_service import PolymarketService
from app.domain.models.polymarket import PolymarketSnapshot


@pytest.mark.anyio
async def test_polymarket_service_fetch_and_filter(db_session, mocker):
    # Mock Gamma API response
    mock_response_data = [
        {
            "id": "1",
            "conditionId": "cond1",
            "question": "Will Bitcoin price reach $100k in 2026?",
            "description": "Bitcoin resolution",
            "outcomePrices": '["0.65", "0.35"]',
            "liquidity": "150000.00",
            "volume": "500000.00",
            "volume24h": "25000.00",
            "endDate": "2026-12-31T23:59:00Z",
            "active": True,
            "category": "Crypto"
        },
        {
            "id": "2",
            "conditionId": "cond2",
            "question": "Will Donald Trump win the 2028 election?",
            "description": "Politics resolution",
            "outcomePrices": '["0.45", "0.55"]',
            "liquidity": "1000000.00",
            "volume": "5000000.00",
            "volume24h": "150000.00",
            "endDate": "2028-11-07T23:59:00Z",
            "active": True,
            "category": "Politics"
        },
        {
            "id": "3",
            "conditionId": "cond3",
            "question": "Will Ethereum gas fees drop below 5 gwei?",
            "description": "ETH gas fees",
            "outcomePrices": '["0.20", "0.80"]',
            "liquidity": "10000.00",
            "volume": "30000.00",
            "volume24h": "2000.00",
            "endDate": "2026-08-30T00:00:00Z",
            "active": True,
            "category": "Crypto"
        }
    ]

    # Mock httpx.AsyncClient
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_response_data
    mock_resp.raise_for_status = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    
    mocker.patch("httpx.AsyncClient", return_value=mock_client)

    service = PolymarketService(db_session)
    markets = await service.fetch_crypto_markets(limit=10)

    # Politics market (id=2) should be filtered out
    assert len(markets) == 2
    
    m1 = next(m for m in markets if m.condition_id == "cond1")
    assert m1.question == "Will Bitcoin price reach $100k in 2026?"
    assert m1.outcome_yes_price == Decimal("0.65")
    assert m1.probability == 0.65
    assert m1.liquidity == Decimal("150000.00")
    assert m1.volume == Decimal("500000.00")
    assert m1.active is True
    
    m2 = next(m for m in markets if m.condition_id == "cond3")
    assert m2.question == "Will Ethereum gas fees drop below 5 gwei?"
    assert m2.outcome_yes_price == Decimal("0.20")
    assert m2.probability == 0.20

    # Verify stored in DB
    snapshots = await service.get_latest_insights()
    assert len(snapshots) == 2


@pytest.mark.anyio
async def test_polymarket_service_summary(db_session):
    # Populate DB with mock snapshots manually
    fetched_at = datetime.now(UTC)
    snap1 = PolymarketSnapshot(
        condition_id="c1",
        question="Will Bitcoin hit $100k?",
        outcome_yes_price=Decimal("0.60"),
        outcome_no_price=Decimal("0.40"),
        liquidity=Decimal("1000.00"),
        volume=Decimal("5000.00"),
        volume_24h=Decimal("500.00"),
        active=True,
        fetched_at=fetched_at
    )
    snap2 = PolymarketSnapshot(
        condition_id="c2",
        question="Will Solana hit $500?",
        outcome_yes_price=Decimal("0.30"),
        outcome_no_price=Decimal("0.70"),
        liquidity=Decimal("2000.00"),
        volume=Decimal("8000.00"),
        volume_24h=Decimal("800.00"),
        active=True,
        fetched_at=fetched_at
    )
    db_session.add(snap1)
    db_session.add(snap2)
    await db_session.commit()

    service = PolymarketService(db_session)
    summary = await service.get_summary()

    assert summary.total_markets == 2
    assert summary.avg_probability == pytest.approx(0.45)
    assert summary.total_liquidity == Decimal("3000.00")
    assert len(summary.markets) == 2
