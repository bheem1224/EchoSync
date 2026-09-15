"""add_entity_aliases_and_attributes

Revision ID: d4a8e2b9c1f0
Revises: a1b2c3d4e5f6
Create Date: 2026-09-12 20:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4a8e2b9c1f0"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Ensure track_aliases table exists and has plugin_id
    if "track_aliases" in tables:
        cols = [c["name"] for c in inspector.get_columns("track_aliases")]
        if "plugin_id" not in cols:
            op.add_column("track_aliases", sa.Column("plugin_id", sa.Integer(), nullable=True))
            op.create_index("ix_track_aliases_plugin_id", "track_aliases", ["plugin_id"])
    else:
        op.create_table(
            "track_aliases",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "track_id", sa.Integer(), sa.ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False, index=True
            ),
            sa.Column("plugin_id", sa.Integer(), nullable=True, index=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("locale", sa.String(), nullable=True),
            sa.Column("script", sa.String(), nullable=True),
            sa.Column("is_primary_for_locale", sa.Boolean(), server_default="0", default=False),
            sa.UniqueConstraint("track_id", "locale", "script", "name", name="uq_track_alias"),
        )

    # 2. Ensure artist_aliases table exists and has plugin_id & alias_type
    if "artist_aliases" in tables:
        cols = [c["name"] for c in inspector.get_columns("artist_aliases")]
        if "plugin_id" not in cols:
            op.add_column("artist_aliases", sa.Column("plugin_id", sa.Integer(), nullable=True))
            op.create_index("ix_artist_aliases_plugin_id", "artist_aliases", ["plugin_id"])
        if "alias_type" not in cols:
            op.add_column(
                "artist_aliases", sa.Column("alias_type", sa.String(length=50), server_default="default", nullable=True)
            )
    else:
        op.create_table(
            "artist_aliases",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "artist_id", sa.Integer(), sa.ForeignKey("artists.id", ondelete="CASCADE"), nullable=False, index=True
            ),
            sa.Column("plugin_id", sa.Integer(), nullable=True, index=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("locale", sa.String(), nullable=True),
            sa.Column("script", sa.String(), nullable=True),
            sa.Column("alias_type", sa.String(length=50), server_default="default", nullable=True),
            sa.Column("is_primary_for_locale", sa.Boolean(), server_default="0", default=False),
            sa.UniqueConstraint("artist_id", "locale", "script", "name", name="uq_artist_alias"),
        )

    # 3. Create track_attributes
    if "track_attributes" not in tables:
        op.create_table(
            "track_attributes",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "track_id", sa.Integer(), sa.ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False, index=True
            ),
            sa.Column("plugin_id", sa.Integer(), nullable=False, index=True),
            sa.Column("key", sa.String(length=100), nullable=False),
            sa.Column("value", sa.JSON(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("track_id", "plugin_id", "key", name="uq_track_attributes_entity_plugin_key"),
        )
        op.create_index("ix_track_attributes_plugin_key", "track_attributes", ["plugin_id", "key"])

    # 4. Create artist_attributes
    if "artist_attributes" not in tables:
        op.create_table(
            "artist_attributes",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "artist_id", sa.Integer(), sa.ForeignKey("artists.id", ondelete="CASCADE"), nullable=False, index=True
            ),
            sa.Column("plugin_id", sa.Integer(), nullable=False, index=True),
            sa.Column("key", sa.String(length=100), nullable=False),
            sa.Column("value", sa.JSON(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("artist_id", "plugin_id", "key", name="uq_artist_attributes_entity_plugin_key"),
        )
        op.create_index("ix_artist_attributes_plugin_key", "artist_attributes", ["plugin_id", "key"])

    # 5. Create album_attributes
    if "album_attributes" not in tables:
        op.create_table(
            "album_attributes",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "album_id", sa.Integer(), sa.ForeignKey("albums.id", ondelete="CASCADE"), nullable=False, index=True
            ),
            sa.Column("plugin_id", sa.Integer(), nullable=False, index=True),
            sa.Column("key", sa.String(length=100), nullable=False),
            sa.Column("value", sa.JSON(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("album_id", "plugin_id", "key", name="uq_album_attributes_entity_plugin_key"),
        )
        op.create_index("ix_album_attributes_plugin_key", "album_attributes", ["plugin_id", "key"])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "album_attributes" in tables:
        op.drop_table("album_attributes")
    if "artist_attributes" in tables:
        op.drop_table("artist_attributes")
    if "track_attributes" in tables:
        op.drop_table("track_attributes")
