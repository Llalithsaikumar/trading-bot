"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-05 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, index=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("username", sa.String(50), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("role", sa.String(20), nullable=False, server_default="trader"),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending_verification"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_email_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("two_fa_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("two_fa_secret", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    # ── portfolios ────────────────────────────────────────────────────────────
    op.create_table(
        "portfolios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, index=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("exchange", sa.String(50), nullable=False),
        sa.Column("quote_currency", sa.String(10), nullable=False, server_default="USDT"),
        sa.Column("total_value_usdt", sa.Numeric(20, 8), nullable=False, server_default="0"),
        sa.Column("available_balance", sa.Numeric(20, 8), nullable=False, server_default="0"),
        sa.Column("unrealized_pnl", sa.Numeric(20, 8), nullable=False, server_default="0"),
        sa.Column("realized_pnl", sa.Numeric(20, 8), nullable=False, server_default="0"),
        sa.Column("daily_pnl", sa.Numeric(20, 8), nullable=False, server_default="0"),
        sa.Column("is_paper_trading", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # ── strategies ────────────────────────────────────────────────────────────
    op.create_table(
        "strategies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, index=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("exchange", sa.String(50), nullable=False),
        sa.Column("symbols", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("timeframe", sa.String(10), nullable=False, server_default="1h"),
        sa.Column("status", sa.String(20), nullable=False, server_default="paused"),
        sa.Column("max_position_size_pct", sa.Numeric(5, 2), nullable=False, server_default="5.0"),
        sa.Column("stop_loss_pct", sa.Numeric(5, 2), nullable=False, server_default="2.0"),
        sa.Column("take_profit_pct", sa.Numeric(5, 2), nullable=False, server_default="4.0"),
        sa.Column("max_open_positions", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("config", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("total_trades", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("winning_trades", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_pnl", sa.Numeric(20, 8), nullable=False, server_default="0"),
        sa.Column("sharpe_ratio", sa.Numeric(10, 4), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_strategies_status", "strategies", ["status"])

    # ── positions ─────────────────────────────────────────────────────────────
    op.create_table(
        "positions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, index=True),
        sa.Column(
            "portfolio_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("portfolios.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("symbol", sa.String(20), nullable=False, index=True),
        sa.Column("side", sa.String(10), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 8), nullable=False),
        sa.Column("entry_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("current_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("liquidation_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("leverage", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("margin_used", sa.Numeric(20, 8), nullable=False, server_default="0"),
        sa.Column("unrealized_pnl", sa.Numeric(20, 8), nullable=False, server_default="0"),
        sa.Column("unrealized_pnl_pct", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("stop_loss", sa.Numeric(20, 8), nullable=True),
        sa.Column("take_profit", sa.Numeric(20, 8), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # ── orders ────────────────────────────────────────────────────────────────
    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, index=True),
        sa.Column(
            "portfolio_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("portfolios.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("exchange_order_id", sa.String(100), nullable=True, index=True),
        sa.Column("symbol", sa.String(20), nullable=False, index=True),
        sa.Column("exchange", sa.String(50), nullable=False),
        sa.Column("side", sa.String(10), nullable=False),
        sa.Column("order_type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending", index=True),
        sa.Column("time_in_force", sa.String(10), nullable=False, server_default="GTC"),
        sa.Column("quantity", sa.Numeric(20, 8), nullable=False),
        sa.Column("price", sa.Numeric(20, 8), nullable=True),
        sa.Column("filled_quantity", sa.Numeric(20, 8), nullable=False, server_default="0"),
        sa.Column("average_fill_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("fee", sa.Numeric(20, 8), nullable=False, server_default="0"),
        sa.Column("fee_currency", sa.String(10), nullable=True),
        sa.Column("stop_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("reduce_only", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "strategy_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("strategies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("agent_reasoning", sa.String(2000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # ── strategy_executions ───────────────────────────────────────────────────
    op.create_table(
        "strategy_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, index=True),
        sa.Column(
            "strategy_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("strategies.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("run_id", sa.String(100), nullable=True, index=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("signal", sa.String(20), nullable=True),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # ── ohlcv ─────────────────────────────────────────────────────────────────
    op.create_table(
        "ohlcv",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, index=True),
        sa.Column("exchange", sa.String(50), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("timeframe", sa.String(10), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(20, 8), nullable=False),
        sa.Column("high", sa.Numeric(20, 8), nullable=False),
        sa.Column("low", sa.Numeric(20, 8), nullable=False),
        sa.Column("close", sa.Numeric(20, 8), nullable=False),
        sa.Column("volume", sa.Numeric(30, 8), nullable=False),
        sa.Column("quote_volume", sa.Numeric(30, 8), nullable=True),
        sa.Column("trades_count", sa.BigInteger(), nullable=True),
        sa.UniqueConstraint("exchange", "symbol", "timeframe", "timestamp", name="uq_ohlcv"),
    )
    op.create_index("ix_ohlcv_symbol_tf_ts", "ohlcv", ["symbol", "timeframe", "timestamp"])

    # ── market_tickers ────────────────────────────────────────────────────────
    op.create_table(
        "market_tickers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, index=True),
        sa.Column("exchange", sa.String(50), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False, index=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bid", sa.Numeric(20, 8), nullable=True),
        sa.Column("ask", sa.Numeric(20, 8), nullable=True),
        sa.Column("last", sa.Numeric(20, 8), nullable=True),
        sa.Column("mark_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("index_price", sa.Numeric(20, 8), nullable=True),
        sa.Column("volume_24h", sa.Numeric(30, 8), nullable=True),
        sa.Column("quote_volume_24h", sa.Numeric(30, 8), nullable=True),
        sa.Column("change_24h_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("high_24h", sa.Numeric(20, 8), nullable=True),
        sa.Column("low_24h", sa.Numeric(20, 8), nullable=True),
        sa.Column("funding_rate", sa.Numeric(12, 8), nullable=True),
        sa.UniqueConstraint("exchange", "symbol", name="uq_ticker"),
    )

    # ── alerts ────────────────────────────────────────────────────────────────
    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, index=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("symbol", sa.String(20), nullable=False, index=True),
        sa.Column("alert_type", sa.String(30), nullable=False),
        sa.Column("condition_value", sa.Numeric(20, 8), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_triggered", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notify_email", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notify_push", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("alerts")
    op.drop_table("market_tickers")
    op.drop_index("ix_ohlcv_symbol_tf_ts", table_name="ohlcv")
    op.drop_table("ohlcv")
    op.drop_table("strategy_executions")
    op.drop_table("orders")
    op.drop_table("positions")
    op.drop_index("ix_strategies_status", table_name="strategies")
    op.drop_table("strategies")
    op.drop_table("portfolios")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
