"""repair_audio_fingerprints_schema

Revision ID: e2f3a4b5c6d7
Revises: d3e4f5a6b7c8
Create Date: 2026-09-04 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2f3a4b5c6d7'
down_revision: Union[str, None] = 'd3e4f5a6b7c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS _alembic_tmp_audio_fingerprints (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            media_id VARCHAR(8) NOT NULL,
            chromaprint VARCHAR NOT NULL,
            acoustid_id VARCHAR,
            CONSTRAINT uq_audio_fingerprints_media_id UNIQUE (media_id),
            FOREIGN KEY (media_id) REFERENCES local_media (media_id) ON DELETE CASCADE
        );
    """))
    conn.execute(sa.text("""
        INSERT INTO _alembic_tmp_audio_fingerprints (id, media_id, chromaprint, acoustid_id)
        SELECT id, media_id, chromaprint, acoustid_id FROM audio_fingerprints;
    """))
    conn.execute(sa.text("DROP TABLE audio_fingerprints;"))
    conn.execute(sa.text("ALTER TABLE _alembic_tmp_audio_fingerprints RENAME TO audio_fingerprints;"))
    conn.execute(sa.text("CREATE INDEX ix_audio_fingerprints_chromaprint ON audio_fingerprints (chromaprint);"))
    conn.execute(sa.text("CREATE INDEX ix_audio_fingerprints_media_id ON audio_fingerprints (media_id);"))


def downgrade() -> None:
    pass
