"""v2.5.4 — Migrate services.beta_opt_in to channel_preference

Migrates nullable integer beta_opt_in to an explicit string channel_preference column
('inherit', 'beta', 'stable') with SQLite batch mode, preserving backward compatibility.

Revision ID: b4c6d8e0f2a4
Revises: a3b5c7d9e1f3
Create Date: 2026-09-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b4c6d8e0f2a4"
down_revision: str | None = "a3b5c7d9e1f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("services")]

    if "channel_preference" not in columns:
        with op.batch_alter_table("services", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "channel_preference",
                    sa.String(length=16),
                    server_default="inherit",
                    nullable=False,
                )
            )

    # Data migration: populate channel_preference from existing beta_opt_in values
    op.execute("UPDATE services SET channel_preference = 'beta' WHERE beta_opt_in = 1")
    op.execute("UPDATE services SET channel_preference = 'stable' WHERE beta_opt_in = 0")
    op.execute(
        "UPDATE services SET channel_preference = 'inherit' WHERE beta_opt_in IS NULL OR beta_opt_in NOT IN (0, 1)"
    )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("services")]

    if "channel_preference" in columns:
        # Sync back to beta_opt_in
        op.execute("UPDATE services SET beta_opt_in = 1 WHERE channel_preference = 'beta'")
        op.execute("UPDATE services SET beta_opt_in = 0 WHERE channel_preference = 'stable'")
        op.execute("UPDATE services SET beta_opt_in = NULL WHERE channel_preference = 'inherit'")

        with op.batch_alter_table("services", schema=None) as batch_op:
            batch_op.drop_column("channel_preference")
