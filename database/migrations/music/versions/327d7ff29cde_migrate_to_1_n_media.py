"""migrate_to_1_n_media

Revision ID: 327d7ff29cde
Revises: eaf4b5d2df68
Create Date: 2026-06-17 23:02:06.827490

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "327d7ff29cde"
down_revision: str | None = "eaf4b5d2df68"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    import random
    import string

    def generate_nanoid(size=8):
        alphabet = string.ascii_letters + string.digits
        return "".join(random.choices(alphabet, k=size))

    # 1. Create local_media table
    op.create_table(
        "local_media",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("media_id", sa.String(length=8), nullable=False),
        sa.Column(
            "track_id",
            sa.Integer(),
            sa.ForeignKey("tracks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("file_format", sa.String(), nullable=True),
        sa.Column("bitrate", sa.Integer(), nullable=True),
        sa.Column("sample_rate", sa.Integer(), nullable=True),
        sa.Column("bit_depth", sa.Integer(), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("inode", sa.BigInteger(), nullable=True),
        sa.Column("mtime", sa.Float(), nullable=True),
        sa.Column("added_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        op.f("ix_local_media_media_id"), "local_media", ["media_id"], unique=True
    )
    op.create_index(
        op.f("ix_local_media_track_id"), "local_media", ["track_id"], unique=False
    )
    op.create_index(
        op.f("ix_local_media_inode"), "local_media", ["inode"], unique=False
    )
    op.create_index(
        "ix_local_media_file_path", "local_media", ["file_path"], unique=True
    )

    # 2. Add media_id to audio_fingerprints and external_identifiers
    with op.batch_alter_table("audio_fingerprints") as batch_op:
        batch_op.add_column(sa.Column("media_id", sa.String(length=8), nullable=True))
    with op.batch_alter_table("external_identifiers") as batch_op:
        batch_op.add_column(sa.Column("media_id", sa.String(length=8), nullable=True))

    # 3. Data migration
    connection = op.get_bind()
    tracks = connection.execute(
        sa.text(
            "SELECT id, sync_id, file_path, file_format, bitrate, sample_rate, bit_depth, file_size_bytes, inode, mtime, added_at FROM tracks"
        )
    ).fetchall()

    for track in tracks:
        new_sync_id = generate_nanoid()
        connection.execute(
            sa.text("UPDATE tracks SET sync_id = :sid WHERE id = :tid"),
            {"sid": new_sync_id, "tid": track.id},
        )

        if track.file_path:
            new_media_id = generate_nanoid()
            connection.execute(
                sa.text("""
                INSERT INTO local_media (media_id, track_id, file_path, file_format, bitrate, sample_rate, bit_depth, file_size_bytes, inode, mtime, added_at)
                VALUES (:mid, :tid, :fp, :ff, :br, :sr, :bd, :fsb, :ino, :mtime, :add)
            """),
                {
                    "mid": new_media_id,
                    "tid": track.id,
                    "fp": track.file_path,
                    "ff": track.file_format,
                    "br": track.bitrate,
                    "sr": track.sample_rate,
                    "bd": track.bit_depth,
                    "fsb": track.file_size_bytes,
                    "ino": track.inode,
                    "mtime": track.mtime,
                    "add": track.added_at,
                },
            )

    # Update audio_fingerprints and external_identifiers media_id
    connection.execute(
        sa.text("""
        UPDATE audio_fingerprints
        SET media_id = (
            SELECT lm.media_id FROM local_media lm
            WHERE lm.track_id = audio_fingerprints.track_id
            LIMIT 1
        )
    """)
    )
    connection.execute(sa.text("DELETE FROM audio_fingerprints WHERE media_id IS NULL"))

    connection.execute(
        sa.text("""
        UPDATE external_identifiers
        SET media_id = (
            SELECT lm.media_id FROM local_media lm
            WHERE lm.track_id = external_identifiers.track_id
            LIMIT 1
        )
    """)
    )

    # Strictly delete proprietary identifiers (not mapped to media_server)
    connection.execute(
        sa.text(
            "DELETE FROM external_identifiers WHERE plugin_source IN ('spotify', 'deezer', 'tidal', 'apple_music')"
        )
    )
    connection.execute(
        sa.text("DELETE FROM external_identifiers WHERE media_id IS NULL")
    )

    # 4. Alter columns to NOT NULL and add ForeignKeys
    with op.batch_alter_table("audio_fingerprints") as batch_op:
        batch_op.drop_index("ix_audio_fingerprints_track_id")
        batch_op.drop_column("track_id")
        batch_op.alter_column("media_id", nullable=False)
        batch_op.create_foreign_key(
            "fk_audio_fp_media",
            "local_media",
            ["media_id"],
            ["media_id"],
            ondelete="CASCADE",
        )
        batch_op.create_index(
            batch_op.f("ix_audio_fingerprints_media_id"), ["media_id"], unique=False
        )

    with op.batch_alter_table("external_identifiers") as batch_op:
        batch_op.drop_index("ix_external_identifiers_track_id")
        batch_op.drop_column("track_id")
        batch_op.alter_column("media_id", nullable=False)
        batch_op.create_foreign_key(
            "fk_ext_id_media",
            "local_media",
            ["media_id"],
            ["media_id"],
            ondelete="CASCADE",
        )
        batch_op.create_index(
            batch_op.f("ix_external_identifiers_media_id"), ["media_id"], unique=False
        )

    # 5. Alter tracks table
    with op.batch_alter_table("tracks") as batch_op:
        batch_op.drop_index("ix_tracks_inode")
        batch_op.drop_column("file_path")
        batch_op.drop_column("file_format")
        batch_op.drop_column("bitrate")
        batch_op.drop_column("sample_rate")
        batch_op.drop_column("bit_depth")
        batch_op.drop_column("file_size_bytes")
        batch_op.drop_column("inode")
        batch_op.drop_column("mtime")


def downgrade() -> None:
    pass
