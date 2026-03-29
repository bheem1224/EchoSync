"""Add track_aliases and artist_aliases tables

Revision ID: f3a9c1e82d47
Revises: cb4f02f432ea
Create Date: 2026-03-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3a9c1e82d47'
down_revision: Union[str, None] = 'cb4f02f432ea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'track_aliases',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('track_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('locale', sa.String(), nullable=True),
        sa.Column('script', sa.String(), nullable=True),
        sa.Column('is_primary_for_locale', sa.Boolean(), server_default='0', nullable=False),
        sa.ForeignKeyConstraint(['track_id'], ['tracks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('track_id', 'locale', 'script', 'name', name='uq_track_alias'),
    )
    with op.batch_alter_table('track_aliases', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_track_aliases_track_id'), ['track_id'], unique=False)

    op.create_table(
        'artist_aliases',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('artist_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('locale', sa.String(), nullable=True),
        sa.Column('script', sa.String(), nullable=True),
        sa.Column('is_primary_for_locale', sa.Boolean(), server_default='0', nullable=False),
        sa.ForeignKeyConstraint(['artist_id'], ['artists.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('artist_id', 'locale', 'script', 'name', name='uq_artist_alias'),
    )
    with op.batch_alter_table('artist_aliases', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_artist_aliases_artist_id'), ['artist_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('artist_aliases', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_artist_aliases_artist_id'))
    op.drop_table('artist_aliases')

    with op.batch_alter_table('track_aliases', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_track_aliases_track_id'))
    op.drop_table('track_aliases')
