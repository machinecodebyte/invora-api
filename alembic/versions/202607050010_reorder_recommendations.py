"""Reorder recommendations.

Revision ID: 202607050010
Revises: 202607050009
Create Date: 2026-07-09 18:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202607050010"
down_revision: str | None = "202607050009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reorder_recommendations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("forecast_run_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("predicted_demand", sa.Numeric(14, 3), nullable=False),
        sa.Column("current_stock", sa.Numeric(14, 3), nullable=False),
        sa.Column("minimum_stock", sa.Numeric(14, 3), nullable=False),
        sa.Column("safety_stock", sa.Numeric(14, 3), nullable=False),
        sa.Column("required_stock", sa.Numeric(14, 3), nullable=False),
        sa.Column("reorder_quantity", sa.Numeric(14, 3), nullable=False),
        sa.Column("stock_gap", sa.Numeric(14, 3), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("recommended_action", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["forecast_run_id"],
            ["forecast_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "forecast_run_id",
            "product_id",
            name="uq_reorder_recommendations_run_product",
        ),
    )
    op.create_index(
        op.f("ix_reorder_recommendations_forecast_run_id"),
        "reorder_recommendations",
        ["forecast_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reorder_recommendations_generated_at"),
        "reorder_recommendations",
        ["generated_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reorder_recommendations_product_id"),
        "reorder_recommendations",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reorder_recommendations_risk_level"),
        "reorder_recommendations",
        ["risk_level"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reorder_recommendations_status"),
        "reorder_recommendations",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_reorder_recommendations_user_id"),
        "reorder_recommendations",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_reorder_recommendations_user_risk",
        "reorder_recommendations",
        ["user_id", "risk_level"],
        unique=False,
    )
    op.create_index(
        "ix_reorder_recommendations_user_run",
        "reorder_recommendations",
        ["user_id", "forecast_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_reorder_recommendations_user_status",
        "reorder_recommendations",
        ["user_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_reorder_recommendations_user_status",
        table_name="reorder_recommendations",
    )
    op.drop_index(
        "ix_reorder_recommendations_user_run",
        table_name="reorder_recommendations",
    )
    op.drop_index(
        "ix_reorder_recommendations_user_risk",
        table_name="reorder_recommendations",
    )
    op.drop_index(
        op.f("ix_reorder_recommendations_user_id"),
        table_name="reorder_recommendations",
    )
    op.drop_index(
        op.f("ix_reorder_recommendations_status"),
        table_name="reorder_recommendations",
    )
    op.drop_index(
        op.f("ix_reorder_recommendations_risk_level"),
        table_name="reorder_recommendations",
    )
    op.drop_index(
        op.f("ix_reorder_recommendations_product_id"),
        table_name="reorder_recommendations",
    )
    op.drop_index(
        op.f("ix_reorder_recommendations_generated_at"),
        table_name="reorder_recommendations",
    )
    op.drop_index(
        op.f("ix_reorder_recommendations_forecast_run_id"),
        table_name="reorder_recommendations",
    )
    op.drop_table("reorder_recommendations")
