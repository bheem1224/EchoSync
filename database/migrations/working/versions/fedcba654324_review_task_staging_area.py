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
    connection = op.get_bind()
    # Check current columns in SQLite
    inspect_res = connection.execute(sa.text("PRAGMA table_info(review_tasks)")).fetchall()
    existing_columns = [row[1] for row in inspect_res]

    # 1. Add new columns only if they do not exist
    with op.batch_alter_table('review_tasks', schema=None) as batch_op:
        if 'file_path' not in existing_columns:
            batch_op.add_column(sa.Column('file_path', sa.String(), nullable=True))
        if 'track_data' not in existing_columns:
            batch_op.add_column(sa.Column('track_data', sa.JSON(), nullable=True))

    # 2. Migrate existing data from media_id / detected_metadata if they exist
    if 'media_id' in existing_columns or 'detected_metadata' in existing_columns:
        tasks = connection.execute(sa.text("SELECT id, media_id, detected_metadata FROM review_tasks")).fetchall()
        import json
        for task_id, media_id, detected_metadata_str in tasks:
            detected_metadata = {}
            if detected_metadata_str:
                try:
                    detected_metadata = json.loads(detected_metadata_str) if isinstance(detected_metadata_str, str) else detected_metadata_str
                except Exception:
                    pass
            
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
                sa.text("UPDATE review_tasks SET file_path = COALESCE(file_path, :fp), track_data = COALESCE(track_data, :td) WHERE id = :id"),
                {"fp": media_id, "td": json.dumps(track_dict), "id": task_id}
            )

    # 3. Alter columns to be non-nullable, drop old columns, and manage indexes
    with op.batch_alter_table('review_tasks', schema=None) as batch_op:
        # Drop index on media_id if it exists
        try:
            batch_op.drop_index('ix_review_tasks_media_id')
        except Exception:
            pass
        
        # Make new columns non-nullable
        batch_op.alter_column('file_path', nullable=False, existing_type=sa.String())
        batch_op.alter_column('track_data', nullable=False, existing_type=sa.JSON())
        
        # Create index on file_path if it doesn't exist
        try:
            batch_op.create_index(batch_op.f('ix_review_tasks_file_path'), ['file_path'], unique=False)
        except Exception:
            pass
        
        # Drop old columns if they exist
        if 'media_id' in existing_columns:
            batch_op.drop_column('media_id')
        if 'detected_metadata' in existing_columns:
            batch_op.drop_column('detected_metadata')


def downgrade() -> None:
    connection = op.get_bind()
    inspect_res = connection.execute(sa.text("PRAGMA table_info(review_tasks)")).fetchall()
    existing_columns = [row[1] for row in inspect_res]

    # 1. Add old columns back as nullable
    with op.batch_alter_table('review_tasks', schema=None) as batch_op:
        if 'media_id' not in existing_columns:
            batch_op.add_column(sa.Column('media_id', sa.String(), nullable=True))
        if 'detected_metadata' not in existing_columns:
            batch_op.add_column(sa.Column('detected_metadata', sa.JSON(), nullable=True))

    # 2. Restore media_id and detected_metadata from file_path and track_data
    if 'file_path' in existing_columns or 'track_data' in existing_columns:
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
                sa.text("UPDATE review_tasks SET media_id = COALESCE(media_id, :mid), detected_metadata = COALESCE(detected_metadata, :dm) WHERE id = :id"),
                {"mid": file_path, "dm": json.dumps(detected_metadata), "id": task_id}
            )

    # 3. Make media_id non-nullable, drop new columns, and recreate old indexes
    with op.batch_alter_table('review_tasks', schema=None) as batch_op:
        try:
            batch_op.drop_index(batch_op.f('ix_review_tasks_file_path'))
        except Exception:
            pass
        batch_op.alter_column('media_id', nullable=False, existing_type=sa.String())
        try:
            batch_op.create_index('ix_review_tasks_media_id', ['media_id'], unique=False)
        except Exception:
            pass
        if 'file_path' in existing_columns:
            batch_op.drop_column('file_path')
        if 'track_data' in existing_columns:
            batch_op.drop_column('track_data')
