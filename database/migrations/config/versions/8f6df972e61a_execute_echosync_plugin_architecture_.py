"""Execute EchoSync Plugin Architecture Refactor

Revision ID: 8f6df972e61a
Revises: ff09cfb2ca02
Create Date: 2026-04-30 02:28:44.474470

"""
from typing import Sequence, Union
import json
import time

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = '8f6df972e61a'
down_revision: Union[str, None] = 'ff09cfb2ca02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LEGACY_MAPPING = {
    "spotify": "core.spotify",
    "plex": "core.plex",
    "tidal": "core.tidal",
    "listenbrainz": "core.listenbrainz",
    "slskd": "core.slskd"
}

def upgrade() -> None:
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    tables = inspector.get_table_names()

    # Create new config_kvs table if it doesn't exist
    if 'config_kvs' not in tables:
        op.create_table(
            'config_kvs',
            sa.Column('namespace', sa.String(), nullable=False),
            sa.Column('key', sa.String(), nullable=False),
            sa.Column('value', sa.String(), nullable=True),
            sa.Column('is_sensitive', sa.Boolean(), default=False, nullable=False),
            sa.PrimaryKeyConstraint('namespace', 'key')
        )

    # 1. Transform services table logic
    if 'services' in tables:
        columns = [c['name'] for c in inspector.get_columns('services')]
        if 'plugin_id' not in columns: op.add_column('services', sa.Column('plugin_id', sa.String(), nullable=True))
        if 'version_no' not in columns: op.add_column('services', sa.Column('version_no', sa.String(), nullable=True))
        if 'is_enabled' not in columns: op.add_column('services', sa.Column('is_enabled', sa.Boolean(), server_default='1', nullable=False))
        if 'service_type' not in columns: op.add_column('services', sa.Column('service_type', sa.String(), nullable=True))
        if 'created_at' not in columns: op.add_column('services', sa.Column('created_at', sa.Integer(), nullable=True))
        if 'updated_at' not in columns: op.add_column('services', sa.Column('updated_at', sa.Integer(), nullable=True))

        # Update services table with mapped plugin_id
        services_res = conn.execute(text("SELECT id, name FROM services")).fetchall()
        for row in services_res:
            service_id, name = row[0], row[1]
            plugin_id = LEGACY_MAPPING.get(name)
            if plugin_id:
                now = int(time.time())
                conn.execute(
                    text("UPDATE services SET plugin_id = :plugin_id, created_at = :now, updated_at = :now WHERE id = :id"),
                    {"plugin_id": plugin_id, "now": now, "id": service_id}
                )

    # 2. Migrate service_config to config_kvs
    if 'service_config' in tables:
        config_res = conn.execute(text("SELECT service_id, config_key, config_value, is_sensitive FROM service_config")).fetchall()
        for row in config_res:
            service_id, key, value, is_sensitive = row[0], row[1], row[2], row[3]
            if service_id is None:
                # Global config
                conn.execute(
                    text("INSERT INTO config_kvs (namespace, key, value, is_sensitive) VALUES (:namespace, :key, :value, :is_sensitive)"),
                    {"namespace": "global", "key": key, "value": value, "is_sensitive": is_sensitive}
                )
            else:
                # Service specific config
                if 'services' in tables:
                    service_name_res = conn.execute(text("SELECT name FROM services WHERE id = :id"), {"id": service_id}).fetchone()
                    if service_name_res:
                        service_name = service_name_res[0]
                        plugin_id = LEGACY_MAPPING.get(service_name)
                        if plugin_id:
                            if is_sensitive:
                                conn.execute(
                                    text("INSERT INTO account_metadata (account_id, metadata_key, metadata_value) VALUES (0, :key, :value)"),
                                    {"key": f"{plugin_id}_{key}", "value": value}
                                )
                            else:
                                conn.execute(
                                    text("INSERT INTO config_kvs (namespace, key, value, is_sensitive) VALUES (:namespace, :key, :value, 0)"),
                                    {"namespace": plugin_id, "key": key, "value": value}
                                )

    # Migrate accounts
    if 'accounts' in tables:
        accounts_res = conn.execute(text("SELECT id, service_id, account_name, created_at, updated_at FROM accounts")).fetchall()

        columns = [c['name'] for c in inspector.get_columns('accounts')]
        if 'plugin_id' not in columns:
            op.add_column('accounts', sa.Column('plugin_id', sa.String(), nullable=True))

        for row in accounts_res:
            acc_id, service_id, account_name = row[0], row[1], row[2]
            if 'services' in tables:
                service_name_res = conn.execute(text("SELECT name FROM services WHERE id = :id"), {"id": service_id}).fetchone()
                if service_name_res:
                    service_name = service_name_res[0]
                    plugin_id = LEGACY_MAPPING.get(service_name)
                    if plugin_id:
                        conn.execute(
                            text("UPDATE accounts SET plugin_id = :plugin_id WHERE id = :id"),
                            {"plugin_id": plugin_id, "id": acc_id}
                        )
                    else:
                        conn.execute(text("DELETE FROM accounts WHERE id = :id"), {"id": acc_id})


    # Drop legacy columns/tables
    if 'service_config' in tables:
        op.drop_table('service_config')
    # Do NOT drop account_metadata as it contains active user secrets/tokens!

def downgrade() -> None:
    pass
