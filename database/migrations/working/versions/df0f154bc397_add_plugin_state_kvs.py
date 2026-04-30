"""Add plugin_state_kvs

Revision ID: df0f154bc397
Revises: eb2e3f94a5a9
Create Date: 2026-04-30 02:30:19.463162

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'df0f154bc397'
down_revision: Union[str, None] = '0f925200dc0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'plugin_state_kvs',
        sa.Column('namespace', sa.String(), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', sa.String(), nullable=True),
        sa.Column('is_sensitive', sa.Boolean(), default=False, nullable=False),
        sa.PrimaryKeyConstraint('namespace', 'key')
    )


def downgrade() -> None:
    op.drop_table('plugin_state_kvs')
