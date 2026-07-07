"""
API v1 router — aggregates all endpoint modules.
"""

from fastapi import APIRouter

from app.api.v1.endpoints.alerts import router as alerts_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.market_data import router as market_data_router
from app.api.v1.endpoints.orders import router as orders_router
from app.api.v1.endpoints.paper_trading import router as paper_trading_router
from app.api.v1.endpoints.portfolios import router as portfolios_router
from app.api.v1.endpoints.polymarket import router as polymarket_router
from app.api.v1.endpoints.strategies import router as strategies_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.websocket import router as ws_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(portfolios_router, prefix="/portfolios", tags=["Portfolios"])
api_router.include_router(orders_router, prefix="/orders", tags=["Orders"])
api_router.include_router(strategies_router, prefix="/strategies", tags=["Strategies"])
api_router.include_router(market_data_router, prefix="/market", tags=["Market Data"])
api_router.include_router(alerts_router, prefix="/alerts", tags=["Alerts"])
api_router.include_router(ws_router, prefix="/ws", tags=["WebSocket"])
api_router.include_router(paper_trading_router, prefix="/paper", tags=["Paper Trading"])
api_router.include_router(polymarket_router, prefix="/polymarket", tags=["Polymarket Insights"])

