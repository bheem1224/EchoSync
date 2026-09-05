"""v2.5.3 — UI Component Registry

Creates the central ui_components table for the Svelte frontend handshake.
Replaces live ui_manifest.json disk parsing with a single indexed DB query.

Revision ID: a3b5c7d9e1f3
Revises: abcdef123457
Create Date: 2026-05-20

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3b5c7d9e1f3"
down_revision: str | None = "abcdef123457"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("ui_components"):
        op.create_table(
            "ui_components",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("plugin_id", sa.Integer(), nullable=True),
            sa.Column("tag_name", sa.String(), nullable=False),
            sa.Column("component_type", sa.String(), nullable=False),
            sa.Column("entry_path", sa.String(), nullable=False),
            sa.Column("is_core", sa.Boolean(), server_default="0", nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.text("(strftime('%s','now'))"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                server_default=sa.text("(strftime('%s','now'))"),
            ),
        )
        op.create_index(
            "ix_ui_components_tag_name", "ui_components", ["tag_name"], unique=True
        )
        op.create_index("ix_ui_components_plugin_id", "ui_components", ["plugin_id"])
        op.create_index(
            "ix_ui_components_component_type", "ui_components", ["component_type"]
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("ui_components"):
        op.drop_index("ix_ui_components_component_type", table_name="ui_components")
        op.drop_index("ix_ui_components_plugin_id", table_name="ui_components")
        op.drop_index("ix_ui_components_tag_name", table_name="ui_components")
        op.drop_table("ui_components")
