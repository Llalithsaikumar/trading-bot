"""
Add long-term memory schema with pgvector support.

Revision ID: 0003_long_term_memory
Revises: 0002_paper_trading
Create Date: 2026-07-06
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "0003_long_term_memory"
down_revision = "0002_paper_trading"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension (handled in PostgreSQL but ensured here)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "long_term_memories",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "strategy_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("strategies.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("run_id", sa.String(100), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=True),
        sa.Column("signal", sa.String(30), nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("reasoning", sa.Text, nullable=True),
        sa.Column("news_summary", sa.Text, nullable=True),
        sa.Column("indicators_summary", sa.Text, nullable=True),
        sa.Column("performance_summary", sa.Text, nullable=True),
        sa.Column("lessons_learned", sa.Text, nullable=True),
        sa.Column("reflection", sa.Text, nullable=True),
        sa.Column("embedding_text", sa.Text, nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
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


def downgrade() -> None:
    op.drop_table("long_term_memories")
