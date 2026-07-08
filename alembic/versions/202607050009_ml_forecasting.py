"""ML forecasting predictions and metrics.

Revision ID: 202607050009
Revises: 202607050008
Create Date: 2026-07-08 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202607050009"
down_revision: str | None = "202607050008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "forecast_predictions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("forecast_run_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("forecast_date", sa.Date(), nullable=False),
        sa.Column("predicted_demand", sa.Numeric(14, 3), nullable=False),
        sa.Column("model_name", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
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
            "forecast_date",
            name="uq_forecast_predictions_run_product_date",
        ),
    )
    op.create_index(
        op.f("ix_forecast_predictions_forecast_date"),
        "forecast_predictions",
        ["forecast_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_forecast_predictions_forecast_run_id"),
        "forecast_predictions",
        ["forecast_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_forecast_predictions_product_id"),
        "forecast_predictions",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_forecast_predictions_user_id"),
        "forecast_predictions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_forecast_predictions_user_run",
        "forecast_predictions",
        ["user_id", "forecast_run_id"],
        unique=False,
    )

    op.create_table(
        "forecast_model_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("forecast_run_id", sa.Uuid(), nullable=False),
        sa.Column("model_name", sa.String(length=64), nullable=False),
        sa.Column("mae", sa.Numeric(14, 4), nullable=True),
        sa.Column("rmse", sa.Numeric(14, 4), nullable=True),
        sa.Column("mape", sa.Numeric(14, 4), nullable=True),
        sa.Column("training_rows", sa.Integer(), nullable=False),
        sa.Column("validation_rows", sa.Integer(), nullable=False),
        sa.Column("total_products", sa.Integer(), nullable=False),
        sa.Column("fallback_products", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["forecast_run_id"],
            ["forecast_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_forecast_model_metrics_forecast_run_id"),
        "forecast_model_metrics",
        ["forecast_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_forecast_model_metrics_user_id"),
        "forecast_model_metrics",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_forecast_model_metrics_user_run",
        "forecast_model_metrics",
        ["user_id", "forecast_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_forecast_model_metrics_user_run",
        table_name="forecast_model_metrics",
    )
    op.drop_index(
        op.f("ix_forecast_model_metrics_user_id"),
        table_name="forecast_model_metrics",
    )
    op.drop_index(
        op.f("ix_forecast_model_metrics_forecast_run_id"),
        table_name="forecast_model_metrics",
    )
    op.drop_table("forecast_model_metrics")

    op.drop_index(
        "ix_forecast_predictions_user_run",
        table_name="forecast_predictions",
    )
    op.drop_index(
        op.f("ix_forecast_predictions_user_id"),
        table_name="forecast_predictions",
    )
    op.drop_index(
        op.f("ix_forecast_predictions_product_id"),
        table_name="forecast_predictions",
    )
    op.drop_index(
        op.f("ix_forecast_predictions_forecast_run_id"),
        table_name="forecast_predictions",
    )
    op.drop_index(
        op.f("ix_forecast_predictions_forecast_date"),
        table_name="forecast_predictions",
    )
    op.drop_table("forecast_predictions")
