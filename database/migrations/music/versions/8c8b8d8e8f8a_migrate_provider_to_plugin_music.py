"""migrate provider to plugin music

Revision ID: 8c8b8d8e8f8a
Revises: 7b7461716632
Create Date: 2026-05-25 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c8b8d8e8f8a'
down_revision: Union[str, None] = '7b7461716632'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('external_identifiers', schema=None) as batch_op:
        batch_op.alter_column('provider_source', new_column_name='plugin_source', existing_type=sa.String(), nullable=False)
        batch_op.alter_column('provider_item_id', new_column_name='plugin_item_id', existing_type=sa.String(), nullable=False)
        batch_op.drop_constraint('uq_provider_item', type_='unique')
        batch_op.create_unique_constraint('uq_plugin_item', ['plugin_source', 'plugin_item_id'])


def downgrade() -> None:
    with op.batch_alter_table('external_identifiers', schema=None) as batch_op:
        batch_op.alter_column('plugin_source', new_column_name='provider_source', existing_type=sa.String(), nullable=False)
        batch_op.alter_column('plugin_item_id', new_column_name='provider_item_id', existing_type=sa.String(), nullable=False)
        batch_op.drop_constraint('uq_plugin_item', type_='unique')
        batch_op.create_unique_constraint('uq_provider_item', ['provider_source', 'provider_item_id'])
