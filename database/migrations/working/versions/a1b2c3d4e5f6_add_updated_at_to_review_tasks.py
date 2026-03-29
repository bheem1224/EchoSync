"""Add updated_at to review_tasks

Revision ID: a1b2c3d4e5f6
Revises: 4661df33cf8b
Create Date: 2026-03-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import time_utils


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '4661df33cf8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('review_tasks', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'updated_at',
                time_utils.UTCDateTime(),
                nullable=False,
                server_default=sa.text("(strftime('%Y-%m-%dT%H:%M:%S', 'now'))"),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table('review_tasks', schema=None) as batch_op:
        batch_op.drop_column('updated_at')
