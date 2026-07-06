"""
Domain-level exception hierarchy.
HTTP mapping is handled in app/api/middleware/exception_handler.py.
"""
from __future__ import annotations


class AppError(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str, code: str = "APP_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


# ─── Auth ──────────────────────────────────────────────────────────────────────
class AuthenticationError(AppError):
    pass


class AuthorizationError(AppError):
    pass


class TokenExpiredError(AuthenticationError):
    pass


# ─── Resource ─────────────────────────────────────────────────────────────────
class NotFoundError(AppError):
    pass


class AlreadyExistsError(AppError):
    pass


# ─── Trading ──────────────────────────────────────────────────────────────────
class TradingError(AppError):
    pass


class InsufficientBalanceError(TradingError):
    pass


class OrderNotFoundError(NotFoundError):
    pass


class ExchangeError(TradingError):
    pass


class RiskLimitExceededError(TradingError):
    pass


# ─── Agent ────────────────────────────────────────────────────────────────────
class AgentError(AppError):
    pass


class AgentTimeoutError(AgentError):
    pass
