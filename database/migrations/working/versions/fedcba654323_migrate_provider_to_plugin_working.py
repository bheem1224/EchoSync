"""migrate provider to plugin working

Revision ID: fedcba654323
Revises: fedcba654322
Create Date: 2026-05-25 18:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fedcba654323'
down_revision: Union[str, None] = 'fedcba654322'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Alter playback_history table
    # Drop old index and constraint
    with op.batch_alter_table('playback_history', schema=None) as batch_op:
        batch_op.drop_index('ix_playback_history_provider_item_id')
        batch_op.drop_constraint('uq_playback_history', type_='unique')

    # Rename column
    with op.batch_alter_table('playback_history', schema=None) as batch_op:
        batch_op.alter_column('provider_item_id', new_column_name='plugin_item_id', existing_type=sa.String(), nullable=False)

    # Create new index and constraint
    with op.batch_alter_table('playback_history', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_playback_history_plugin_item_id'), ['plugin_item_id'], unique=False)
        batch_op.create_unique_constraint('uq_playback_history', ['user_id', 'plugin_item_id', 'listened_at'])

    # 2. Alter media_server_playlist_items table
    # Drop old index and constraint
    with op.batch_alter_table('media_server_playlist_items', schema=None) as batch_op:
        batch_op.drop_index('ix_media_server_playlist_items_provider_item_id')
        batch_op.drop_constraint('uq_playlist_item', type_='unique')

    # Rename column
    with op.batch_alter_table('media_server_playlist_items', schema=None) as batch_op:
        batch_op.alter_column('provider_item_id', new_column_name='plugin_item_id', existing_type=sa.String(), nullable=False)

    # Create new index and constraint
    with op.batch_alter_table('media_server_playlist_items', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_media_server_playlist_items_plugin_item_id'), ['plugin_item_id'], unique=False)
        batch_op.create_unique_constraint('uq_playlist_item', ['playlist_id', 'plugin_item_id'])


def downgrade() -> None:
    # 1. Reverse media_server_playlist_items table
    # Drop new index and constraint
    with op.batch_alter_table('media_server_playlist_items', schema=None) as batch_op:
        batch_op.drop_index('ix_media_server_playlist_items_plugin_item_id')
        batch_op.drop_constraint('uq_playlist_item', type_='unique')

    # Rename column back
    with op.batch_alter_table('media_server_playlist_items', schema=None) as batch_op:
        batch_op.alter_column('plugin_item_id', new_column_name='provider_item_id', existing_type=sa.String(), nullable=False)

    # Recreate old index and constraint
    with op.batch_alter_table('media_server_playlist_items', schema=None) as batch_op:
        batch_op.create_index('ix_media_server_playlist_items_provider_item_id', ['provider_item_id'], unique=False)
        batch_op.create_unique_constraint('uq_playlist_item', ['playlist_id', 'provider_item_id'])

    # 2. Reverse playback_history table
    # Drop new index and constraint
    with op.batch_alter_table('playback_history', schema=None) as batch_op:
        batch_op.drop_index('ix_playback_history_plugin_item_id')
        batch_op.drop_constraint('uq_playback_history', type_='unique')

    # Rename column back
    with op.batch_alter_table('playback_history', schema=None) as batch_op:
        batch_op.alter_column('plugin_item_id', new_column_name='provider_item_id', existing_type=sa.String(), nullable=False)

    # Recreate old index and constraint
    with op.batch_alter_table('playback_history', schema=None) as batch_op:
        batch_op.create_index('ix_playback_history_provider_item_id', ['provider_item_id'], unique=False)
        batch_op.create_unique_constraint('uq_playback_history', ['user_id', 'provider_item_id', 'listened_at'])
