"""
WebSocket connection manager.
Tracks active connections per user/channel and broadcasts messages.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from fastapi import WebSocket
from loguru import logger


class ConnectionManager:
    """
    Manages WebSocket connections.
    Each user can have multiple connections (different browser tabs / devices).
    Channels allow topic-based broadcasting (ticker, portfolio, signals …).
    """

    def __init__(self) -> None:
        # user_id → set of WebSocket connections
        self._user_connections: dict[str, set[WebSocket]] = defaultdict(set)
        # channel → set of WebSocket connections
        self._channel_subscriptions: dict[str, set[WebSocket]] = defaultdict(set)

    # ── Connection lifecycle ────────────────────────────────────────────────
    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        await websocket.accept()
        self._user_connections[user_id].add(websocket)
        logger.debug("WebSocket connected", user_id=user_id)

    def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        self._user_connections[user_id].discard(websocket)
        # clean up subscriptions
        for subscribers in self._channel_subscriptions.values():
            subscribers.discard(websocket)
        logger.debug("WebSocket disconnected", user_id=user_id)

    # ── Subscriptions ───────────────────────────────────────────────────────
    def subscribe(self, websocket: WebSocket, channel: str) -> None:
        self._channel_subscriptions[channel].add(websocket)

    def unsubscribe(self, websocket: WebSocket, channel: str) -> None:
        self._channel_subscriptions[channel].discard(websocket)

    # ── Sending ─────────────────────────────────────────────────────────────
    async def send_to_user(self, user_id: str, data: dict[str, Any]) -> None:
        """Send a message to all connections of a specific user."""
        dead: set[WebSocket] = set()
        for ws in self._user_connections.get(user_id, set()):
            try:
                await ws.send_json(data)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self._user_connections[user_id].discard(ws)

    async def broadcast_channel(self, channel: str, data: dict[str, Any]) -> None:
        """Broadcast to all subscribers of a channel."""
        dead: set[WebSocket] = set()
        for ws in self._channel_subscriptions.get(channel, set()):
            try:
                await ws.send_json(data)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self._channel_subscriptions[channel].discard(ws)

    @property
    def active_connections_count(self) -> int:
        return sum(len(v) for v in self._user_connections.values())


# Singleton instance — import this everywhere
ws_manager = ConnectionManager()
