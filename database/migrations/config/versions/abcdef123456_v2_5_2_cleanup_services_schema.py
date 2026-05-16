from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'abcdef123456'
down_revision: str = 'abcd12345678' # Note: Assuming this based on the files seen, I will double check
branch_labels = None
depends_on = None

def upgrade() -> None:
    # We must use batch_alter_table for SQLite since it doesn't natively support DROP COLUMN
    # Split into two discrete blocks to avoid topological sort issues (CircularDependencyError)
    
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('services')]

    # Defensive drop for orphaned batch tables from previously failed runs
    op.execute("DROP TABLE IF EXISTS _alembic_tmp_services")

    # Block 1: Drop legacy columns (only if they exist)
    with op.batch_alter_table('services', schema=None) as batch_op:
        if 'namespace' in columns:
            batch_op.drop_column('namespace')
        if 'display_name' in columns:
            batch_op.drop_column('display_name')
        if 'friendly_name' in columns:
            batch_op.drop_column('friendly_name')

    # Block 2: Add new columns (only if they don't exist, NO spatial ordering kwargs)
    with op.batch_alter_table('services', schema=None) as batch_op:
        if 'version' not in columns:
            batch_op.add_column(sa.Column('version', sa.String(), nullable=True))
        if 'plugin_id' not in columns:
            batch_op.add_column(sa.Column('plugin_id', sa.Integer(), nullable=True))
        if 'absolute_install_path' not in columns:
            batch_op.add_column(sa.Column('absolute_install_path', sa.String(), nullable=True))
        if 'loaded_modules' not in columns:
            batch_op.add_column(sa.Column('loaded_modules', sa.String(), nullable=True))

def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('services')]

    with op.batch_alter_table('services', schema=None) as batch_op:
        if 'namespace' not in columns:
            batch_op.add_column(sa.Column('namespace', sa.String(), nullable=False, server_default="legacy"))
        if 'display_name' not in columns:
            batch_op.add_column(sa.Column('display_name', sa.String(), nullable=True))
        if 'friendly_name' not in columns:
            batch_op.add_column(sa.Column('friendly_name', sa.String(), nullable=True))
        
        if 'loaded_modules' in columns:
            batch_op.drop_column('loaded_modules')
        if 'absolute_install_path' in columns:
            batch_op.drop_column('absolute_install_path')
        if 'plugin_id' in columns:
            batch_op.drop_column('plugin_id')
        if 'version' in columns:
            batch_op.drop_column('version')
