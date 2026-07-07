"""Forecast run lifecycle table.

Revision ID: 202607050008
Revises: 202607050007
Create Date: 2026-07-07 16:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202607050008"
down_revision: str | None = "202607050007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "forecast_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.String(length=1000), nullable=True),
        sa.Column("total_products", sa.Integer(), nullable=False),
        sa.Column("total_sales_records", sa.Integer(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_forecast_runs_requested_at"),
        "forecast_runs",
        ["requested_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_forecast_runs_status"),
        "forecast_runs",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_forecast_runs_user_id"),
        "forecast_runs",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_forecast_runs_user_requested_at",
        "forecast_runs",
        ["user_id", "requested_at"],
        unique=False,
    )
    op.create_index(
        "ix_forecast_runs_user_status",
        "forecast_runs",
        ["user_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_forecast_runs_user_status", table_name="forecast_runs")
    op.drop_index("ix_forecast_runs_user_requested_at", table_name="forecast_runs")
    op.drop_index(op.f("ix_forecast_runs_user_id"), table_name="forecast_runs")
    op.drop_index(op.f("ix_forecast_runs_status"), table_name="forecast_runs")
    op.drop_index(op.f("ix_forecast_runs_requested_at"), table_name="forecast_runs")
    op.drop_table("forecast_runs")
