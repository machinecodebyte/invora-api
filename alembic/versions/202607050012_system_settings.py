"""User-scoped system settings.

Revision ID: 202607050012
Revises: 202607050011
Create Date: 2026-07-15 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202607050012"
down_revision: str | None = "202607050011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_system_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "forecast_default_horizon_days",
            sa.Integer(),
            server_default=sa.text("30"),
            nullable=False,
        ),
        sa.Column(
            "forecast_min_history_days",
            sa.Integer(),
            server_default=sa.text("7"),
            nullable=False,
        ),
        sa.Column(
            "forecast_default_model",
            sa.String(length=64),
            server_default=sa.text("'random_forest'"),
            nullable=False,
        ),
        sa.Column(
            "forecast_auto_process_enabled",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column(
            "inventory_default_minimum_stock",
            sa.Numeric(precision=14, scale=3),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "inventory_default_safety_stock",
            sa.Numeric(precision=14, scale=3),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "inventory_low_stock_alert_enabled",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column(
            "sales_upload_duplicate_policy",
            sa.String(length=32),
            server_default=sa.text("'reject'"),
            nullable=False,
        ),
        sa.Column(
            "sales_upload_date_format",
            sa.String(length=32),
            server_default=sa.text("'yyyy-mm-dd'"),
            nullable=False,
        ),
        sa.Column(
            "reports_default_format",
            sa.String(length=16),
            server_default=sa.text("'json'"),
            nullable=False,
        ),
        sa.Column(
            "reports_include_inactive_products",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column(
            "dashboard_default_date_range_days",
            sa.Integer(),
            server_default=sa.text("30"),
            nullable=False,
        ),
        sa.Column(
            "background_jobs_auto_retry_enabled",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column(
            "timezone",
            sa.String(length=64),
            server_default=sa.text("'UTC'"),
            nullable=False,
        ),
        sa.Column(
            "locale",
            sa.String(length=16),
            server_default=sa.text("'en'"),
            nullable=False,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_user_system_settings_user_id"),
    )
    op.create_index(
        op.f("ix_user_system_settings_created_at"),
        "user_system_settings",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_user_system_settings_created_at"),
        table_name="user_system_settings",
    )
    op.drop_table("user_system_settings")
