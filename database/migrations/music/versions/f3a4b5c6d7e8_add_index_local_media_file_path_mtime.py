"""Add index on local_media file_path and mtime

Revision ID: f3a4b5c6d7e8
Revises: d4a8e2b9c1f0
Create Date: 2026-09-20 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3a4b5c6d7e8"
down_revision: str | None = "d4a8e2b9c1f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if "local_media" in tables:
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("local_media")]
        if "ix_local_media_file_path_mtime" not in existing_indexes:
            with op.batch_alter_table("local_media", schema=None) as batch_op:
                batch_op.create_index(
                    "ix_local_media_file_path_mtime",
                    ["file_path", "mtime"],
                    unique=False,
                )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if "local_media" in tables:
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("local_media")]
        if "ix_local_media_file_path_mtime" in existing_indexes:
            with op.batch_alter_table("local_media", schema=None) as batch_op:
                batch_op.drop_index("ix_local_media_file_path_mtime")
