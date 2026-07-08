import pytest
from decimal import Decimal
from datetime import datetime, UTC
from app.domain.models.polymarket import PolymarketSnapshot


@pytest.mark.anyio
async def test_polymarket_endpoints(client, db_session):
    # 1. Register and login to get access token
    register_payload = {
        "email": "testuser_poly@example.com",
        "username": "testuser_poly",
        "password": "strong-password-123",
        "full_name": "Test User Poly",
    }
    response = await client.post("/api/v1/auth/register", json=register_payload)
    assert response.status_code == 201

    login_payload = {
        "email": "testuser_poly@example.com",
        "password": "strong-password-123",
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    login_data = response.json()
    token = login_data["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Add mock snapshot to DB
    fetched_at = datetime.now(UTC)
    snap = PolymarketSnapshot(
        condition_id="c_test_1",
        question="Will Bitcoin exceed $150k?",
        description="Bitcoin prediction",
        outcome_yes_price=Decimal("0.75"),
        outcome_no_price=Decimal("0.25"),
        liquidity=Decimal("250000.00"),
        volume=Decimal("1000000.00"),
        volume_24h=Decimal("50000.00"),
        active=True,
        fetched_at=fetched_at,
    )
    db_session.add(snap)
    await db_session.commit()

    # 3. Test GET /markets endpoint
    response = await client.get("/api/v1/polymarket/markets", headers=headers)
    assert response.status_code == 200
    markets = response.json()
    assert len(markets) == 1
    assert markets[0]["condition_id"] == "c_test_1"
    assert markets[0]["probability"] == 0.75
    assert markets[0]["question"] == "Will Bitcoin exceed $150k?"

    # 4. Test GET /summary endpoint
    response = await client.get("/api/v1/polymarket/summary", headers=headers)
    assert response.status_code == 200
    summary = response.json()
    assert summary["total_markets"] == 1
    assert summary["avg_probability"] == 0.75
    assert Decimal(str(summary["total_liquidity"])) == Decimal("250000.00")

    # 5. Test GET /markets/{condition_id} history endpoint
    response = await client.get("/api/v1/polymarket/markets/c_test_1", headers=headers)
    assert response.status_code == 200
    history = response.json()
    assert len(history) == 1
    assert history[0]["condition_id"] == "c_test_1"

    # Test history endpoint for non-existing market returns 404
    response = await client.get("/api/v1/polymarket/markets/non_existing", headers=headers)
    assert response.status_code == 404
