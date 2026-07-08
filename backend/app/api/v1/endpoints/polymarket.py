"""Polymarket intelligence endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user, get_db
from app.domain.schemas.polymarket import PolymarketMarketResponse, PolymarketSummaryResponse
from app.services.polymarket.polymarket_service import PolymarketService

router = APIRouter()


@router.get("/markets", response_model=list[PolymarketMarketResponse])
async def get_markets(
    limit: int = Query(default=50, ge=1, le=100),
    refresh: bool = Query(default=False),
    session: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    """List active crypto prediction markets on Polymarket."""
    service = PolymarketService(session)
    if refresh:
        return await service.fetch_crypto_markets(limit=limit)
    else:
        return await service.get_latest_insights(limit=limit)


@router.get("/markets/{condition_id}", response_model=list[PolymarketMarketResponse])
async def get_market_history(
    condition_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    """Get the history of snapshots for a specific market."""
    service = PolymarketService(session)
    history = await service.get_market_by_condition_id(condition_id, limit=limit)
    if not history:
        raise HTTPException(status_code=404, detail="Market history not found")
    return history


@router.get("/summary", response_model=PolymarketSummaryResponse)
async def get_summary(
    session: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    """Get summarized intelligence stats for prediction markets."""
    service = PolymarketService(session)
    return await service.get_summary()
