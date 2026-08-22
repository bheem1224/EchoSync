"""add_track_artists_table

Revision ID: c2d3e4f5a6b7
Revises: f1e2d3c4b5a6
Create Date: 2026-08-22 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2d3e4f5a6b7'
down_revision: Union[str, None] = 'f1e2d3c4b5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create track_artists table
    op.create_table(
        'track_artists',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('track_id', sa.Integer(), sa.ForeignKey('tracks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('artist_id', sa.Integer(), sa.ForeignKey('artists.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(), nullable=False, server_default='primary'),
        sa.Column('position', sa.Integer(), nullable=False, server_default='0'),
        sa.UniqueConstraint('track_id', 'artist_id', 'role', name='uq_track_artist_role'),
    )
    op.create_index('ix_track_artists_track_id', 'track_artists', ['track_id'])
    op.create_index('ix_track_artists_artist_id', 'track_artists', ['artist_id'])

    # 2. Backfill existing primary artists from tracks into track_artists
    conn = op.get_bind()
    conn.execute(sa.text("""
        INSERT OR IGNORE INTO track_artists (track_id, artist_id, role, position)
        SELECT id, artist_id, 'primary', 0
        FROM tracks
        WHERE artist_id IS NOT NULL
    """))


def downgrade() -> None:
    op.drop_index('ix_track_artists_artist_id', table_name='track_artists')
    op.drop_index('ix_track_artists_track_id', table_name='track_artists')
    op.drop_table('track_artists')
