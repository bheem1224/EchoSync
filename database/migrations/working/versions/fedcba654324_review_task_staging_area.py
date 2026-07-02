"""review task staging area

Revision ID: fedcba654324
Revises: 22ff0c33fcfc
Create Date: 2026-07-02 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fedcba654324'
down_revision: Union[str, None] = '22ff0c33fcfc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add new columns as nullable first to allow data migration
    with op.batch_alter_table('review_tasks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('file_path', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('track_data', sa.JSON(), nullable=True))

    # 2. Migrate existing media_id to file_path, and construct basic track_data from detected_metadata
    connection = op.get_bind()
    # Fetch existing tasks
    tasks = connection.execute(sa.text("SELECT id, media_id, detected_metadata FROM review_tasks")).fetchall()
    import json
    for task_id, media_id, detected_metadata_str in tasks:
        # Parse detected_metadata if it exists
        detected_metadata = {}
        if detected_metadata_str:
            try:
                detected_metadata = json.loads(detected_metadata_str) if isinstance(detected_metadata_str, str) else detected_metadata_str
            except Exception:
                pass
        
        # Build initial track_data compatible with EchosyncTrack
        # We need raw_title, artist_name, album_title
        title = detected_metadata.get("title") or detected_metadata.get("raw_title") or "Unknown Title"
        artist = detected_metadata.get("artist") or detected_metadata.get("artist_name") or "Unknown Artist"
        album = detected_metadata.get("album") or detected_metadata.get("album_title") or "Unknown Album"
        
        track_dict = {
            "sync_id": None,
            "raw_title": title,
            "title": title,
            "display_title": title,
            "artist": artist,
            "album_artist": detected_metadata.get("album_artist"),
            "album_title": album,
            "edition": detected_metadata.get("edition"),
            "sort_title": detected_metadata.get("sort_title"),
            "artist_sort_name": detected_metadata.get("artist_sort_name"),
            "album_sort_title": detected_metadata.get("album_sort_title"),
            "album_type": detected_metadata.get("album_type"),
            "album_release_group_id": detected_metadata.get("album_release_group_id"),
            "duration_ms": detected_metadata.get("duration") or detected_metadata.get("duration_ms"),
            "track_number": detected_metadata.get("track_number"),
            "disc_number": detected_metadata.get("disc_number"),
            "release_year": detected_metadata.get("year") or detected_metadata.get("release_year"),
            "version": detected_metadata.get("version"),
            "added_at": None,
            "media": [],
            "mbid": detected_metadata.get("musicbrainz_id") or detected_metadata.get("mbid"),
            "isrc": detected_metadata.get("isrc"),
            "acoustid": detected_metadata.get("acoustid_id") or detected_metadata.get("acoustid"),
            "mb_release_id": detected_metadata.get("mb_release_id"),
            "original_release_date": None,
            "fingerprint": detected_metadata.get("fingerprint"),
            "quality_tags": None,
            "is_compilation": None,
            "identifiers": {},
        }
        
        connection.execute(
            sa.text("UPDATE review_tasks SET file_path = :fp, track_data = :td WHERE id = :id"),
            {"fp": media_id, "td": json.dumps(track_dict), "id": task_id}
        )

    # 3. Alter columns to be non-nullable, drop old columns, and manage indexes
    with op.batch_alter_table('review_tasks', schema=None) as batch_op:
        # Drop index on media_id
        batch_op.drop_index('ix_review_tasks_media_id')
        
        # Make new columns non-nullable
        batch_op.alter_column('file_path', nullable=False, existing_type=sa.String())
        batch_op.alter_column('track_data', nullable=False, existing_type=sa.JSON())
        
        # Create index on file_path
        batch_op.create_index(batch_op.f('ix_review_tasks_file_path'), ['file_path'], unique=False)
        
        # Drop old columns
        batch_op.drop_column('media_id')
        batch_op.drop_column('detected_metadata')


def downgrade() -> None:
    # 1. Add old columns back as nullable
    with op.batch_alter_table('review_tasks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('media_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('detected_metadata', sa.JSON(), nullable=True))

    # 2. Restore media_id and detected_metadata from file_path and track_data
    connection = op.get_bind()
    tasks = connection.execute(sa.text("SELECT id, file_path, track_data FROM review_tasks")).fetchall()
    import json
    for task_id, file_path, track_data_str in tasks:
        track_data = {}
        if track_data_str:
            try:
                track_data = json.loads(track_data_str) if isinstance(track_data_str, str) else track_data_str
            except Exception:
                pass
        
        # Map back to detected_metadata format
        detected_metadata = {
            "title": track_data.get("title") or track_data.get("raw_title"),
            "artist": track_data.get("artist"),
            "album": track_data.get("album_title"),
            "year": track_data.get("release_year"),
            "track_number": track_data.get("track_number"),
            "disc_number": track_data.get("disc_number"),
            "musicbrainz_id": track_data.get("mbid"),
            "isrc": track_data.get("isrc"),
            "acoustid_id": track_data.get("acoustid"),
            "mb_release_id": track_data.get("mb_release_id"),
            "fingerprint": track_data.get("fingerprint"),
        }
        
        connection.execute(
            sa.text("UPDATE review_tasks SET media_id = :mid, detected_metadata = :dm WHERE id = :id"),
            {"mid": file_path, "dm": json.dumps(detected_metadata), "id": task_id}
        )

    # 3. Make media_id non-nullable, drop new columns, and recreate old indexes
    with op.batch_alter_table('review_tasks', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_review_tasks_file_path'))
        batch_op.alter_column('media_id', nullable=False, existing_type=sa.String())
        batch_op.create_index('ix_review_tasks_media_id', ['media_id'], unique=False)
        batch_op.drop_column('file_path')
        batch_op.drop_column('track_data')
