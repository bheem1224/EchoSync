from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'abcdef123456'
down_revision: str = 'abcd12345678' # Note: Assuming this based on the files seen, I will double check
branch_labels = None
depends_on = None

def upgrade() -> None:
    # We must use batch_alter_table for SQLite since it doesn't natively support DROP COLUMN
    with op.batch_alter_table('services', schema=None) as batch_op:
        batch_op.drop_column('namespace')
        batch_op.drop_column('display_name')
        batch_op.drop_column('friendly_name')
        batch_op.add_column(sa.Column('version', sa.String(), nullable=True))

def downgrade() -> None:
    with op.batch_alter_table('services', schema=None) as batch_op:
        batch_op.add_column(sa.Column('namespace', sa.String(), nullable=False, server_default="legacy"))
        batch_op.add_column(sa.Column('display_name', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('friendly_name', sa.String(), nullable=True))
        batch_op.drop_column('version')
