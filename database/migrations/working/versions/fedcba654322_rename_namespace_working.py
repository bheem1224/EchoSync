import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fedcba654322"
down_revision: str = "fedcba654321"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("plugin_state_kvs", schema=None) as batch_op:
        batch_op.alter_column(
            "namespace",
            new_column_name="plugin_id",
            existing_type=sa.String(),
            type_=sa.Integer(),
        )


def downgrade() -> None:
    with op.batch_alter_table("plugin_state_kvs", schema=None) as batch_op:
        batch_op.alter_column(
            "plugin_id",
            new_column_name="namespace",
            existing_type=sa.Integer(),
            type_=sa.String(),
        )
