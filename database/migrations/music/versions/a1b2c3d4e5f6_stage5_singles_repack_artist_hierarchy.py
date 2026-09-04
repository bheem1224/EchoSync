"""stage5_singles_repack_artist_hierarchy

Revision ID: a1b2c3d4e5f6
Revises: e2f3a4b5c6d7
Create Date: 2026-09-04 11:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'e2f3a4b5c6d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    # 1. Add release_type to tracks if missing
    track_columns = [c['name'] for c in insp.get_columns('tracks')]
    if 'release_type' not in track_columns:
        with op.batch_alter_table('tracks', schema=None) as batch_op:
            batch_op.add_column(sa.Column('release_type', sa.String(), nullable=True, server_default='album'))
            batch_op.create_index(batch_op.f('ix_tracks_release_type'), ['release_type'], unique=False)

    # 2. Add parent_artist_id to artists if missing
    artist_columns = [c['name'] for c in insp.get_columns('artists')]
    if 'parent_artist_id' not in artist_columns:
        with op.batch_alter_table('artists', schema=None) as batch_op:
            batch_op.add_column(sa.Column('parent_artist_id', sa.Integer(), nullable=True))
            batch_op.create_foreign_key('fk_artists_parent_artist_id', 'artists', ['parent_artist_id'], ['id'], ondelete='SET NULL')
            batch_op.create_index(batch_op.f('ix_artists_parent_artist_id'), ['parent_artist_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('artists', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_artists_parent_artist_id'))
        batch_op.drop_constraint('fk_artists_parent_artist_id', type_='foreignkey')
        batch_op.drop_column('parent_artist_id')

    with op.batch_alter_table('tracks', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_tracks_release_type'))
        batch_op.drop_column('release_type')

