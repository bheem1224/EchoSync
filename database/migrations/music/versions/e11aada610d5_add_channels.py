"""add_channels

Revision ID: e11aada610d5
Revises: 47fc0220d0f9
Create Date: 2026-08-08 21:50:25.522180

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = "e11aada610d5"
down_revision: str | None = "47fc0220d0f9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = [c["name"] for c in inspector.get_columns("local_media")]
    if "channels" not in columns:
        op.add_column("local_media", sa.Column("channels", sa.Integer(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = [c["name"] for c in inspector.get_columns("local_media")]
    if "channels" in columns:
        op.drop_column("local_media", "channels")
