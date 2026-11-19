"""Wave 2: Canonical verification tiers, edition version_type, duration_ms index, and WITHOUT ROWID junctions.

Revision ID: g1a2b3c4d5e6
Revises: f3a4b5c6d7e8
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "g1a2b3c4d5e6"
down_revision: str | None = "f3a4b5c6d7e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "tracks" in tables:
        track_cols = {c["name"] for c in inspector.get_columns("tracks")}
        track_indexes = {idx["name"] for idx in inspector.get_indexes("tracks")}

        if "verification_tier" not in track_cols:
            op.add_column(
                "tracks",
                sa.Column("verification_tier", sa.String(), nullable=False, server_default="unverified"),
            )
        if "canonical_mbid" not in track_cols:
            op.add_column("tracks", sa.Column("canonical_mbid", sa.String(), nullable=True))
        if "version_type" not in track_cols:
            op.add_column(
                "tracks",
                sa.Column("version_type", sa.String(), nullable=False, server_default="original"),
            )
        if "enhancement_attempts" not in track_cols:
            op.add_column(
                "tracks",
                sa.Column("enhancement_attempts", sa.Integer(), nullable=False, server_default="0"),
            )

        op.execute(
            "UPDATE tracks SET verification_tier = 'quarantined', musicbrainz_id = NULL "
            "WHERE musicbrainz_id = 'NOT_FOUND'"
        )

        if "ix_tracks_verification_tier" not in track_indexes:
            op.create_index("ix_tracks_verification_tier", "tracks", ["verification_tier"])
        if "ix_tracks_canonical_mbid" not in track_indexes:
            op.create_index("ix_tracks_canonical_mbid", "tracks", ["canonical_mbid"])
        if "ix_tracks_version_type" not in track_indexes:
            op.create_index("ix_tracks_version_type", "tracks", ["version_type"])
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_tracks_unverified ON tracks (id) "
            "WHERE verification_tier = 'unverified'"
        )

    if "local_media" in tables:
        media_cols = {c["name"] for c in inspector.get_columns("local_media")}
        media_indexes = {idx["name"] for idx in inspector.get_indexes("local_media")}
        if "duration_ms" not in media_cols:
            op.add_column("local_media", sa.Column("duration_ms", sa.Integer(), nullable=True))
        if "ix_local_media_duration_ms" not in media_indexes:
            op.create_index("ix_local_media_duration_ms", "local_media", ["duration_ms"])

    if "track_artist_aliases" in tables:
        op.execute("PRAGMA foreign_keys=OFF")
        op.execute("DROP TABLE IF EXISTS track_artist_aliases")
        op.execute("PRAGMA foreign_keys=ON")

    if "track_artists" in tables:
        ta_cols = {c["name"] for c in inspector.get_columns("track_artists")}
        if "id" in ta_cols:
            op.execute("PRAGMA foreign_keys=OFF")
            op.execute("DROP TABLE IF EXISTS track_artists__new")
            op.execute(
                """
                CREATE TABLE track_artists__new (
                    track_id INTEGER NOT NULL,
                    artist_id INTEGER NOT NULL,
                    role VARCHAR NOT NULL DEFAULT 'primary',
                    position INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (track_id, artist_id, role),
                    FOREIGN KEY(track_id) REFERENCES tracks (id) ON DELETE CASCADE,
                    FOREIGN KEY(artist_id) REFERENCES artists (id) ON DELETE CASCADE
                ) WITHOUT ROWID
                """
            )
            op.execute(
                """
                INSERT OR IGNORE INTO track_artists__new (track_id, artist_id, role, position)
                SELECT track_id, artist_id, COALESCE(role, 'primary'), MIN(COALESCE(position, 0))
                FROM track_artists
                GROUP BY track_id, artist_id, COALESCE(role, 'primary')
                """
            )
            op.execute("DROP TABLE track_artists")
            op.execute("ALTER TABLE track_artists__new RENAME TO track_artists")
            op.execute("CREATE INDEX IF NOT EXISTS ix_track_artists_track_id ON track_artists (track_id)")
            op.execute("CREATE INDEX IF NOT EXISTS ix_track_artists_artist_id ON track_artists (artist_id)")
            op.execute("PRAGMA foreign_keys=ON")

    if "albums" in tables and "album_artists" not in tables:
        op.execute(
            """
            CREATE TABLE IF NOT EXISTS album_artists (
                album_id INTEGER NOT NULL,
                artist_id INTEGER NOT NULL,
                role VARCHAR NOT NULL DEFAULT 'primary',
                position INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (album_id, artist_id, role),
                FOREIGN KEY(album_id) REFERENCES albums (id) ON DELETE CASCADE,
                FOREIGN KEY(artist_id) REFERENCES artists (id) ON DELETE CASCADE
            ) WITHOUT ROWID
            """
        )
        op.execute("CREATE INDEX IF NOT EXISTS ix_album_artists_album_id ON album_artists (album_id)")
        op.execute("CREATE INDEX IF NOT EXISTS ix_album_artists_artist_id ON album_artists (artist_id)")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "album_artists" in tables:
        op.drop_table("album_artists")

    if "local_media" in tables:
        media_indexes = {idx["name"] for idx in inspector.get_indexes("local_media")}
        media_cols = {c["name"] for c in inspector.get_columns("local_media")}
        if "ix_local_media_duration_ms" in media_indexes:
            op.drop_index("ix_local_media_duration_ms", table_name="local_media")
        if "duration_ms" in media_cols:
            with op.batch_alter_table("local_media") as batch_op:
                batch_op.drop_column("duration_ms")

    if "tracks" in tables:
        op.execute("DROP INDEX IF EXISTS ix_tracks_unverified")
        track_indexes = {idx["name"] for idx in inspector.get_indexes("tracks")}
        track_cols = {c["name"] for c in inspector.get_columns("tracks")}
        for idx_name in ("ix_tracks_version_type", "ix_tracks_canonical_mbid", "ix_tracks_verification_tier"):
            if idx_name in track_indexes:
                op.drop_index(idx_name, table_name="tracks")
        with op.batch_alter_table("tracks") as batch_op:
            for col_name in ("enhancement_attempts", "version_type", "canonical_mbid", "verification_tier"):
                if col_name in track_cols:
                    batch_op.drop_column(col_name)
