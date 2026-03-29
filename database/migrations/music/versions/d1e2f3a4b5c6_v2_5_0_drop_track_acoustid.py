"""Drop acoustid_id column from tracks table

AcoustID fingerprint data belongs exclusively in the audio_fingerprints table
(track_id, fingerprint_hash, acoustid_id).  Having a redundant acoustid_id
column on tracks created two sources of truth that could drift out of sync.

Revision ID: d1e2f3a4b5c6
Revises: f3a9c1e82d47
Create Date: 2026-03-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, None] = 'f3a9c1e82d47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite requires batch mode to drop columns.
    with op.batch_alter_table('tracks', schema=None) as batch_op:
        batch_op.drop_column('acoustid_id')


def downgrade() -> None:
    with op.batch_alter_table('tracks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('acoustid_id', sa.String(), nullable=True))
