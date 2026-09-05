"""Stage 1: download_queue state machine and candidate stack migration

Revision ID: fedcba654325
Revises: ba366761575f
Create Date: 2026-09-03 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fedcba654325"
down_revision: str | None = "ba366761575f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    # Inspect existing columns on download_queue
    table_info = connection.execute(
        sa.text("PRAGMA table_info(download_queue)")
    ).fetchall()
    existing_columns = {row[1] for row in table_info}

    # Inspect existing indexes
    index_info = connection.execute(
        sa.text("PRAGMA index_list(download_queue)")
    ).fetchall()
    existing_indexes = {row[1] for row in index_info}

    with op.batch_alter_table("download_queue", schema=None) as batch_op:
        if "intent" not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    "intent",
                    sa.String(32),
                    nullable=False,
                    server_default="MANUAL_OMNI",
                )
            )
        if "active_candidate_id" not in existing_columns:
            batch_op.add_column(
                sa.Column("active_candidate_id", sa.String(128), nullable=True)
            )
        if "candidate_stack" not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    "candidate_stack", sa.JSON(), nullable=False, server_default="[]"
                )
            )
        if "blacklisted_candidates" not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    "blacklisted_candidates",
                    sa.JSON(),
                    nullable=False,
                    server_default="[]",
                )
            )
        if "error_reason" not in existing_columns:
            batch_op.add_column(
                sa.Column("error_reason", sa.String(255), nullable=True)
            )
        if "plugin_id" not in existing_columns:
            if "provider_id" in existing_columns:
                batch_op.alter_column(
                    "provider_id",
                    new_column_name="plugin_id",
                    existing_type=sa.String(128),
                    nullable=True,
                )
            else:
                batch_op.add_column(
                    sa.Column("plugin_id", sa.String(128), nullable=True)
                )
        if "retry_count" not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    "retry_count", sa.Integer(), nullable=False, server_default="0"
                )
            )
        if "sync_id" in existing_columns:
            batch_op.alter_column(
                "sync_id",
                existing_type=sa.String(64),
                nullable=True,
            )

        # Ensure index on status
        if "ix_download_queue_status" not in existing_indexes:
            batch_op.create_index("ix_download_queue_status", ["status"], unique=False)
        # Ensure index on sync_id
        if "ix_download_queue_sync_id" not in existing_indexes:
            batch_op.create_index(
                "ix_download_queue_sync_id", ["sync_id"], unique=False
            )

    # Normalize existing status values to uppercase
    connection.execute(
        sa.text(
            "UPDATE download_queue SET status = UPPER(status) WHERE status IS NOT NULL"
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("download_queue", schema=None) as batch_op:
        batch_op.drop_index("ix_download_queue_status")
        batch_op.drop_column("error_reason")
        batch_op.drop_column("blacklisted_candidates")
        batch_op.drop_column("candidate_stack")
        batch_op.drop_column("active_candidate_id")
        batch_op.drop_column("intent")
