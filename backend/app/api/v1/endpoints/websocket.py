"""
WebSocket endpoints.
Each endpoint corresponds to a real-time data stream.
"""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.constants import (
    WS_CHANNEL_PORTFOLIO,
    WS_CHANNEL_SIGNALS,
    WS_CHANNEL_TICKER,
)
from app.infrastructure.messaging.websocket_manager import ws_manager

router = APIRouter()


@router.websocket("/ticker/{exchange}/{symbol}")
async def ticker_stream(
    websocket: WebSocket,
    exchange: str,
    symbol: str,
) -> None:
    """Stream real-time price ticks for a trading pair."""
    user_id = "anonymous"  # TODO: authenticate from query param token
    await ws_manager.connect(websocket, user_id)
    channel = f"{WS_CHANNEL_TICKER}:{exchange}:{symbol}"
    ws_manager.subscribe(websocket, channel)
    try:
        while True:
            # Keep the connection alive; data is pushed via ws_manager.broadcast_channel()
            await websocket.receive_text()
            # handle ping/pong or subscription changes
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, user_id)


@router.websocket("/portfolio/{portfolio_id}")
async def portfolio_stream(
    websocket: WebSocket,
    portfolio_id: str,
) -> None:
    """Stream live portfolio updates (PnL, balance, positions)."""
    user_id = "anonymous"  # TODO: authenticate
    await ws_manager.connect(websocket, user_id)
    ws_manager.subscribe(websocket, f"{WS_CHANNEL_PORTFOLIO}:{portfolio_id}")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, user_id)


@router.websocket("/signals")
async def signals_stream(websocket: WebSocket) -> None:
    """Stream AI trading signals as they are generated."""
    user_id = "anonymous"  # TODO: authenticate
    await ws_manager.connect(websocket, user_id)
    ws_manager.subscribe(websocket, WS_CHANNEL_SIGNALS)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, user_id)
