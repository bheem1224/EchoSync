"""v2.5.1_plugin_architecture_updates

Revision ID: abcd12345678
Revises: dccb620740d1
Create Date: 2026-05-10 21:40:43.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "abcd12345678"
down_revision: str | None = "dccb620740d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Get current tables
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # Drop deprecated tables
    if "account_metadata" in tables:
        op.drop_table("account_metadata")
    if "config_kvs" in tables:
        op.drop_table("config_kvs")

    # Add version to services table
    if "services" in tables:
        columns = [c["name"] for c in inspector.get_columns("services")]
        if "version" not in columns:
            op.add_column("services", sa.Column("version", sa.TEXT(), nullable=True))


def downgrade() -> None:
    # Recreate tables (optional but good practice)
    op.create_table(
        "account_metadata",
        sa.Column("id", sa.INTEGER(), nullable=False),
        sa.Column("account_id", sa.INTEGER(), nullable=False),
        sa.Column("metadata_key", sa.TEXT(), nullable=False),
        sa.Column("metadata_value", sa.TEXT(), nullable=True),
        sa.Column(
            "created_at",
            sa.INTEGER(),
            server_default=sa.text("(strftime('%s','now'))"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.INTEGER(),
            server_default=sa.text("(strftime('%s','now'))"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "metadata_key"),
    )

    op.create_table(
        "config_kvs",
        sa.Column("namespace", sa.TEXT(), nullable=False),
        sa.Column("key", sa.TEXT(), nullable=False),
        sa.Column("value", sa.TEXT(), nullable=True),
        sa.Column(
            "is_sensitive", sa.INTEGER(), server_default=sa.text("0"), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.INTEGER(),
            server_default=sa.text("(strftime('%s','now'))"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.INTEGER(),
            server_default=sa.text("(strftime('%s','now'))"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("namespace", "key"),
    )

    # Drop version column from services (sqlite doesn't easily support dropping columns without batch_alter_table)
    with op.batch_alter_table("services", schema=None) as batch_op:
        batch_op.drop_column("version")
