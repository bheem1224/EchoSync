"""Rename audio_fingerprints.fingerprint_hash to chromaprint

The column stores the raw locally-generated Chromaprint string.  Renaming it
to 'chromaprint' makes the schema unambiguous:

  chromaprint  — raw string output of the Chromaprint algorithm (our local computation)
  acoustid_id  — UUID returned by the AcoustID service after a successful lookup
                 (the external service's canonical identifier for this recording)

Revision ID: e7f8a9b0c1d2
Revises: d1e2f3a4b5c6
Create Date: 2026-03-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7f8a9b0c1d2'
down_revision: Union[str, None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite requires batch mode for column renames.
    with op.batch_alter_table('audio_fingerprints', schema=None) as batch_op:
        batch_op.alter_column('fingerprint_hash', new_column_name='chromaprint')


def downgrade() -> None:
    with op.batch_alter_table('audio_fingerprints', schema=None) as batch_op:
        batch_op.alter_column('chromaprint', new_column_name='fingerprint_hash')
