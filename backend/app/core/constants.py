"""Application-wide constants (no config — pure literals)."""

from __future__ import annotations

# Queue names
QUEUE_DEFAULT = "default"
QUEUE_TRADING = "trading"
QUEUE_MARKET_DATA = "market_data"
QUEUE_NOTIFICATIONS = "notifications"

# Redis key prefixes
REDIS_PREFIX_SESSION = "session:"
REDIS_PREFIX_RATE_LIMIT = "rate_limit:"
REDIS_PREFIX_MARKET = "market:"
REDIS_PREFIX_LOCK = "lock:"

# WebSocket channels
WS_CHANNEL_TICKER = "ticker"
WS_CHANNEL_ORDERBOOK = "orderbook"
WS_CHANNEL_TRADES = "trades"
WS_CHANNEL_PORTFOLIO = "portfolio"
WS_CHANNEL_SIGNALS = "signals"
WS_CHANNEL_ALERTS = "alerts"

# Trading
DEFAULT_TIMEFRAME = "1h"
SUPPORTED_TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
MAX_ORDER_HISTORY = 1000

# Pagination
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
