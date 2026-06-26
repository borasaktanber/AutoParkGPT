"""initial schema: reservations + dynamic data

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-26
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reservations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("first_name", sa.String(length=128), nullable=False),
        sa.Column("last_name", sa.String(length=128), nullable=False),
        sa.Column("car_number", sa.String(length=32), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "working_hours",
        sa.Column("day_of_week", sa.Integer(), primary_key=True),
        sa.Column("opens", sa.String(length=5), nullable=False),
        sa.Column("closes", sa.String(length=5), nullable=False),
        sa.Column("is_closed", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "prices",
        sa.Column("label", sa.String(length=64), primary_key=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("unit", sa.String(length=16), nullable=False),
    )
    op.create_table(
        "availability",
        sa.Column("zone", sa.String(length=64), primary_key=True),
        sa.Column("total_spaces", sa.Integer(), nullable=False),
        sa.Column("free_spaces", sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("availability")
    op.drop_table("prices")
    op.drop_table("working_hours")
    op.drop_table("reservations")
