"""Add suggestion_intents table

Revision ID: 0f925200dc0f
Revises: a1b2c3d4e5f6
Create Date: 2026-04-24 12:18:57.533097

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import time_utils

# revision identifiers, used by Alembic.
revision: str = '0f925200dc0f'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'suggestion_intents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sync_id', sa.String(), nullable=True),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('originator', sa.String(), nullable=False),
        sa.Column('track_name', sa.String(), nullable=False),
        sa.Column('track_id', sa.Integer(), nullable=True),
        sa.Column('action_needed', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, default="PENDING_APPROVAL"),
        sa.Column('admin_exempt_deletion', sa.Boolean(), nullable=False, default=False),
        sa.Column('admin_force_upgrade', sa.Boolean(), nullable=False, default=False),
        sa.Column('execute_at', time_utils.UTCDateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_suggestion_intents_sync_id'), 'suggestion_intents', ['sync_id'], unique=False)
    op.create_index(op.f('ix_suggestion_intents_track_id'), 'suggestion_intents', ['track_id'], unique=False)
    op.create_index(op.f('ix_suggestion_intents_status'), 'suggestion_intents', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_suggestion_intents_status'), table_name='suggestion_intents')
    op.drop_index(op.f('ix_suggestion_intents_track_id'), table_name='suggestion_intents')
    op.drop_index(op.f('ix_suggestion_intents_sync_id'), table_name='suggestion_intents')
    op.drop_table('suggestion_intents')
