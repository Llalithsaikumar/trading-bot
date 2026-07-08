"""Market data endpoints — live prices via ccxt."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_active_user, get_exchange_client
from app.core.exceptions import ExchangeError
from app.domain.schemas.market_data import (
    MarketSummaryResponse,
    OHLCVResponse,
    OrderBookResponse,
    TickerResponse,
)
from app.infrastructure.exchange.base import BaseExchange

router = APIRouter()


@router.get("/ticker/{exchange}/{symbol}", response_model=TickerResponse)
async def get_ticker(
    symbol: str,
    exchange: str,
    exc: BaseExchange = Depends(get_exchange_client),
    _=Depends(get_current_active_user),
):
    raw = await exc.fetch_ticker(symbol)
    return TickerResponse(
        exchange=exchange,
        symbol=symbol,
        timestamp=str(raw.get("timestamp", "")),
        bid=Decimal(str(raw.get("bid") or raw.get("last") or 0)),
        ask=Decimal(str(raw.get("ask") or raw.get("last") or 0)),
        last=Decimal(str(raw.get("last") or 0)),
        volume_24h=Decimal(str(raw.get("quoteVolume") or raw.get("baseVolume") or 0)),
        change_24h_pct=Decimal(str(raw.get("percentage") or 0)),
        high_24h=Decimal(str(raw.get("high") or 0)) if raw.get("high") else None,
        low_24h=Decimal(str(raw.get("low") or 0)) if raw.get("low") else None,
        funding_rate=None,
    )


@router.get("/ohlcv/{exchange}/{symbol}", response_model=list[OHLCVResponse])
async def get_ohlcv(
    symbol: str,
    exchange: str,
    timeframe: str = Query(default="1h"),
    limit: int = Query(default=100, ge=1, le=1000),
    exc: BaseExchange = Depends(get_exchange_client),
    _=Depends(get_current_active_user),
):
    candles = await exc.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    return [
        OHLCVResponse(
            timestamp=str(c[0]),
            open=Decimal(str(c[1])),
            high=Decimal(str(c[2])),
            low=Decimal(str(c[3])),
            close=Decimal(str(c[4])),
            volume=Decimal(str(c[5])),
        )
        for c in candles
    ]


@router.get("/orderbook/{exchange}/{symbol}", response_model=OrderBookResponse)
async def get_order_book(
    symbol: str,
    exchange: str,
    depth: int = Query(default=20, ge=5, le=100),
    exc: BaseExchange = Depends(get_exchange_client),
    _=Depends(get_current_active_user),
):
    book = await exc.fetch_order_book(symbol, limit=depth)
    return OrderBookResponse(
        exchange=exchange,
        symbol=symbol,
        bids=[[Decimal(str(p)), Decimal(str(s))] for p, s in (book.get("bids") or [])[:depth]],
        asks=[[Decimal(str(p)), Decimal(str(s))] for p, s in (book.get("asks") or [])[:depth]],
        timestamp=str(book.get("timestamp", "")),
    )


@router.get("/summary", response_model=list[MarketSummaryResponse])
async def get_market_summary(
    exchange: str = Query(default="binance"),
    symbols: list[str] = Query(default=["BTC/USDT", "ETH/USDT"]),
    exc: BaseExchange = Depends(get_exchange_client),
    _=Depends(get_current_active_user),
):
    results = []
    for sym in symbols[:10]:
        try:
            raw = await exc.fetch_ticker(sym)
            results.append(
                MarketSummaryResponse(
                    exchange=exchange,
                    symbol=sym,
                    last=Decimal(str(raw.get("last") or 0)),
                    change_24h_pct=Decimal(str(raw.get("percentage") or 0)),
                    volume_24h=Decimal(str(raw.get("quoteVolume") or 0)),
                    high_24h=Decimal(str(raw.get("high") or 0)) if raw.get("high") else None,
                    low_24h=Decimal(str(raw.get("low") or 0)) if raw.get("low") else None,
                )
            )
        except ExchangeError:
            pass
    return results
