"""
Add paper trading infrastructure:
  - portfolios.initial_balance column
  - equity_history table for PnL / risk-metric time series

Revision ID: 0002_paper_trading
Revises: 0001_initial_schema
Create Date: 2026-07-05
"""


from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_paper_trading"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Add initial_balance to portfolios ────────────────────────────────────
    op.add_column(
        "portfolios",
        sa.Column(
            "initial_balance",
            sa.Numeric(20, 8),
            nullable=False,
            server_default="0",
            comment="Starting balance; used to compute total return",
        ),
    )

    # ── Create equity_history table ──────────────────────────────────────────
    op.create_table(
        "equity_history",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "portfolio_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("portfolios.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("equity", sa.Numeric(20, 8), nullable=False),
        sa.Column("balance", sa.Numeric(20, 8), nullable=False),
        sa.Column("unrealized_pnl", sa.Numeric(20, 8), nullable=False, server_default="0"),
        sa.Column("realized_pnl", sa.Numeric(20, 8), nullable=False, server_default="0"),
        sa.Column("daily_pnl", sa.Numeric(20, 8), nullable=False, server_default="0"),
    )

    op.create_index("ix_equity_history_portfolio_id", "equity_history", ["portfolio_id"])
    op.create_index("ix_equity_history_timestamp", "equity_history", ["timestamp"])


def downgrade() -> None:
    op.drop_table("equity_history")
    op.drop_column("portfolios", "initial_balance")
