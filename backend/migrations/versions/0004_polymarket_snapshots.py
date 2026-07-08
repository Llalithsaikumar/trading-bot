"""
Add polymarket snapshots schema.

Revision ID: 0004_polymarket_snapshots
Revises: 0003_long_term_memory
Create Date: 2026-07-07
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_polymarket_snapshots"
down_revision = "0003_long_term_memory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "polymarket_snapshots",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("condition_id", sa.String(255), nullable=False, index=True),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("outcome_yes_price", sa.Numeric(10, 4), nullable=False),
        sa.Column("outcome_no_price", sa.Numeric(10, 4), nullable=False),
        sa.Column("liquidity", sa.Numeric(20, 2), nullable=False),
        sa.Column("volume", sa.Numeric(20, 2), nullable=False),
        sa.Column("volume_24h", sa.Numeric(20, 2), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_index(
        "ix_polymarket_snapshots_condition_fetched",
        "polymarket_snapshots",
        ["condition_id", "fetched_at"],
    )


def downgrade() -> None:
    op.drop_table("polymarket_snapshots")
