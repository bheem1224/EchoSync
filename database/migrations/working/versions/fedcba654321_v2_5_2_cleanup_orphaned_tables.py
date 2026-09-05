from alembic import op
from sqlalchemy.engine import reflection

# revision identifiers, used by Alembic.
revision: str = "fedcba654321"
down_revision: str = "0560a1c7fa89"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Aggressively drop all prv_ and cache_ tables from working.db
    # Now that plugins have their own isolated SQLite databases, they shouldn't be polluting working.db
    conn = op.get_bind()
    inspector = reflection.Inspector.from_engine(conn)
    tables = inspector.get_table_names()

    for table in tables:
        if table.startswith("prv_") or table.startswith("cache_"):
            op.drop_table(table)


def downgrade() -> None:
    # Downgrading cannot restore dropped data tables dynamically created by plugins.
    pass
