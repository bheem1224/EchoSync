"""add_fts5_tracks_table

Revision ID: b5f9e8a7c1d2
Revises: 327d7ff29cde
Create Date: 2026-07-29 13:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5f9e8a7c1d2'
down_revision: Union[str, None] = '327d7ff29cde'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create FTS5 Virtual Table for Full-Text Search on tracks
    op.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS tracks_fts USING fts5(
            title,
            artist,
            album,
            content='tracks',
            content_rowid='id'
        );
    """)

    # 2. Create triggers to keep tracks_fts synchronized with tracks, artists, and albums
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS tracks_ai AFTER INSERT ON tracks BEGIN
            INSERT INTO tracks_fts(rowid, title, artist, album)
            VALUES (
                new.id,
                new.title,
                (SELECT name FROM artists WHERE id = new.artist_id),
                (SELECT title FROM albums WHERE id = new.album_id)
            );
        END;
    """)

    op.execute("""
        CREATE TRIGGER IF NOT EXISTS tracks_ad AFTER DELETE ON tracks BEGIN
            INSERT INTO tracks_fts(tracks_fts, rowid, title, artist, album)
            VALUES (
                'delete',
                old.id,
                old.title,
                (SELECT name FROM artists WHERE id = old.artist_id),
                (SELECT title FROM albums WHERE id = old.album_id)
            );
        END;
    """)

    op.execute("""
        CREATE TRIGGER IF NOT EXISTS tracks_au AFTER UPDATE ON tracks BEGIN
            INSERT INTO tracks_fts(tracks_fts, rowid, title, artist, album)
            VALUES (
                'delete',
                old.id,
                old.title,
                (SELECT name FROM artists WHERE id = old.artist_id),
                (SELECT title FROM albums WHERE id = old.album_id)
            );
            INSERT INTO tracks_fts(rowid, title, artist, album)
            VALUES (
                new.id,
                new.title,
                (SELECT name FROM artists WHERE id = new.artist_id),
                (SELECT title FROM albums WHERE id = new.album_id)
            );
        END;
    """)

    # 3. Populate FTS index for existing tracks
    op.execute("""
        INSERT INTO tracks_fts(rowid, title, artist, album)
        SELECT 
            t.id, 
            t.title, 
            a.name, 
            alb.title 
        FROM tracks t
        LEFT JOIN artists a ON t.artist_id = a.id
        LEFT JOIN albums alb ON t.album_id = alb.id;
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS tracks_au;")
    op.execute("DROP TRIGGER IF EXISTS tracks_ad;")
    op.execute("DROP TRIGGER IF EXISTS tracks_ai;")
    op.execute("DROP TABLE IF EXISTS tracks_fts;")
