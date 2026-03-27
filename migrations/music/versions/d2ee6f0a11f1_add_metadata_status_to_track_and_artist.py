"""add_metadata_status_to_track_and_artist

Revision ID: d2ee6f0a11f1
Revises: 4a0a9825ea5c
Create Date: 2026-03-27 13:06:32.412935

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd2ee6f0a11f1'
down_revision: Union[str, Sequence[str], None] = '4a0a9825ea5c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — idempotent: guards each ADD COLUMN against pre-existing columns."""
    bind = op.get_bind()

    # --- artists.metadata_status ---
    artist_cols = {row[1] for row in bind.execute(sa.text("PRAGMA table_info(artists)"))}
    if "metadata_status" not in artist_cols:
        with op.batch_alter_table("artists", schema=None) as batch_op:
            batch_op.add_column(sa.Column("metadata_status", sa.JSON(), nullable=True))

    # --- tracks.metadata_status ---
    track_cols = {row[1] for row in bind.execute(sa.text("PRAGMA table_info(tracks)"))}
    if "metadata_status" not in track_cols:
        with op.batch_alter_table("tracks", schema=None) as batch_op:
            batch_op.add_column(sa.Column("metadata_status", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("tracks", schema=None) as batch_op:
        batch_op.drop_column("metadata_status")

    with op.batch_alter_table("artists", schema=None) as batch_op:
        batch_op.drop_column("metadata_status")
