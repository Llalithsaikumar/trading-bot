"""
Central configuration loaded from environment variables / .env file.
Uses Pydantic v2 BaseSettings for type-safe, validated config.
"""

from __future__ import annotations

from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────────────────────
    APP_NAME: str = "CryptoTrader AI"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_DEBUG: bool = False
    APP_SECRET_KEY: str
    APP_ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1"]

    # ── API ────────────────────────────────────────────────────────────────────
    API_V1_PREFIX: str = "/api/v1"
    API_PORT: int = 8000

    # ── JWT ────────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Database ───────────────────────────────────────────────────────────────
    DATABASE_URL: str  # postgresql+asyncpg://...
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_ECHO: bool = False

    # ── Redis ──────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ── Exchange ───────────────────────────────────────────────────────────────
    EXCHANGE_DEFAULT: str = "binance"

    BINANCE_API_KEY: str = ""
    BINANCE_API_SECRET: str = ""
    BINANCE_TESTNET: bool = True

    BYBIT_API_KEY: str = ""
    BYBIT_API_SECRET: str = ""
    BYBIT_TESTNET: bool = True

    OKX_API_KEY: str = ""
    OKX_API_SECRET: str = ""
    OKX_PASSPHRASE: str = ""
    OKX_DEMO: bool = True

    HYPERLIQUID_WALLET_ADDRESS: str = ""
    HYPERLIQUID_PRIVATE_KEY: str = ""

    # Legacy — kept for env-file compatibility; not used by the exchange factory.
    COINBASE_API_KEY: str = ""
    COINBASE_API_SECRET: str = ""
    KRAKEN_API_KEY: str = ""
    KRAKEN_API_SECRET: str = ""

    # ── LLM ───────────────────────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    LLM_MODEL: str = "claude-sonnet-4-6"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 4096

    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "crypto-trader"

    # ── Logging ────────────────────────────────────────────────────────────────
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FORMAT: Literal["json", "text"] = "json"
    LOG_FILE_PATH: str = "logs/app.log"

    # ── CORS ───────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ── WebSocket ──────────────────────────────────────────────────────────────
    WS_HEARTBEAT_INTERVAL: int = 30

    # ── Risk ───────────────────────────────────────────────────────────────────
    MAX_POSITION_SIZE_PCT: float = 10.0
    MAX_DAILY_LOSS_PCT: float = 5.0
    DEFAULT_STOP_LOSS_PCT: float = 2.0
    DEFAULT_TAKE_PROFIT_PCT: float = 4.0

    # ── Monitoring ─────────────────────────────────────────────────────────────
    PROMETHEUS_ENABLED: bool = True

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("APP_ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [h.strip() for h in v.split(",")]
        return v


# Singleton – import this everywhere
settings = Settings()  # type: ignore[call-arg]
