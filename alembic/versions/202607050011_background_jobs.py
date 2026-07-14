"""Background jobs.

Revision ID: 202607050011
Revises: 202607050010
Create Date: 2026-07-14 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202607050011"
down_revision: str | None = "202607050010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "background_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("rq_job_id", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=True),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("queue_name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("enqueued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.Column(
            "result_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "job_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_background_jobs_created_at"),
        "background_jobs",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_background_jobs_enqueued_at"),
        "background_jobs",
        ["enqueued_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_background_jobs_entity_id"),
        "background_jobs",
        ["entity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_background_jobs_job_type"),
        "background_jobs",
        ["job_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_background_jobs_queue_name"),
        "background_jobs",
        ["queue_name"],
        unique=False,
    )
    op.create_index(
        "ix_background_jobs_queue_status",
        "background_jobs",
        ["queue_name", "status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_background_jobs_rq_job_id"),
        "background_jobs",
        ["rq_job_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_background_jobs_status"),
        "background_jobs",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_background_jobs_user_entity",
        "background_jobs",
        ["user_id", "entity_id"],
        unique=False,
    )
    op.create_index(
        "ix_background_jobs_user_job_type",
        "background_jobs",
        ["user_id", "job_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_background_jobs_user_id"),
        "background_jobs",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_background_jobs_user_status",
        "background_jobs",
        ["user_id", "status"],
        unique=False,
    )
    op.create_index(
        "uq_background_jobs_active_forecast_run",
        "background_jobs",
        ["job_type", "entity_type", "entity_id"],
        unique=True,
        postgresql_where=sa.text(
            "status IN ('queued', 'started', 'retrying') "
            "AND entity_type = 'forecast_run' "
            "AND entity_id IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_background_jobs_active_forecast_run",
        table_name="background_jobs",
        postgresql_where=sa.text(
            "status IN ('queued', 'started', 'retrying') "
            "AND entity_type = 'forecast_run' "
            "AND entity_id IS NOT NULL"
        ),
    )
    op.drop_index("ix_background_jobs_user_status", table_name="background_jobs")
    op.drop_index(op.f("ix_background_jobs_user_id"), table_name="background_jobs")
    op.drop_index("ix_background_jobs_user_job_type", table_name="background_jobs")
    op.drop_index("ix_background_jobs_user_entity", table_name="background_jobs")
    op.drop_index(op.f("ix_background_jobs_status"), table_name="background_jobs")
    op.drop_index(op.f("ix_background_jobs_rq_job_id"), table_name="background_jobs")
    op.drop_index("ix_background_jobs_queue_status", table_name="background_jobs")
    op.drop_index(op.f("ix_background_jobs_queue_name"), table_name="background_jobs")
    op.drop_index(op.f("ix_background_jobs_job_type"), table_name="background_jobs")
    op.drop_index(op.f("ix_background_jobs_entity_id"), table_name="background_jobs")
    op.drop_index(op.f("ix_background_jobs_enqueued_at"), table_name="background_jobs")
    op.drop_index(op.f("ix_background_jobs_created_at"), table_name="background_jobs")
    op.drop_table("background_jobs")
