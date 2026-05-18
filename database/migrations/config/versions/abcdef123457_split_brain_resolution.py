from alembic import op
import sqlalchemy as sa

revision = 'abcdef123457'
down_revision = 'abcdef123456'
branch_labels = None
depends_on = None

def upgrade() -> None:
    with op.batch_alter_table('services', schema=None) as batch_op:
        batch_op.add_column(sa.Column('beta_opt_in', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('previous_version_path', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('verified_source', sa.Boolean(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('privileged_mode', sa.Boolean(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('permissions', sa.String(), server_default='[]', nullable=False))

def downgrade() -> None:
    with op.batch_alter_table('services', schema=None) as batch_op:
        batch_op.drop_column('permissions')
        batch_op.drop_column('privileged_mode')
        batch_op.drop_column('verified_source')
        batch_op.drop_column('previous_version_path')
        batch_op.drop_column('beta_opt_in')
