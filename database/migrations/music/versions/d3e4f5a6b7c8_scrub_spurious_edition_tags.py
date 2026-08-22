"""scrub_spurious_edition_tags

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-08-22 17:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3e4f5a6b7c8'
down_revision: Union[str, None] = 'c2d3e4f5a6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE tracks 
        SET edition = NULL 
        WHERE edition IS NOT NULL 
          AND LOWER(title) NOT LIKE '%remix%'
          AND LOWER(title) NOT LIKE '%mix%'
          AND LOWER(title) NOT LIKE '%live%'
          AND LOWER(title) NOT LIKE '%acoustic%'
          AND LOWER(title) NOT LIKE '%instrumental%'
          AND LOWER(title) NOT LIKE '%karaoke%'
          AND LOWER(title) NOT LIKE '%deluxe%'
          AND LOWER(title) NOT LIKE '%edit%'
          AND LOWER(title) NOT LIKE '%version%'
    """))


def downgrade() -> None:
    pass
