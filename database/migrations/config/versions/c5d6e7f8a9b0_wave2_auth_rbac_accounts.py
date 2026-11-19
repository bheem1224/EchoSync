"""Wave 2: Local-first users, roles, WITHOUT ROWID assignments, API keys, and granted_scopes.

Revision ID: c5d6e7f8a9b0
Revises: b4c6d8e0f2a4
Create Date: 2026-11-18
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c5d6e7f8a9b0"
down_revision: str | None = "b4c6d8e0f2a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MEMBER_PERMISSIONS = [
    "contract:tracks:read",
    "contract:albums:read",
    "contract:artists:read",
    "contract:playlists:read:own",
    "contract:playlists:edit:own",
    "contract:accounts:read:own",
    "service:library:read",
    "service:playlist_sync:edit",
    "service:requests:enrich",
    "service:requests:auto_approve",
    "service:suggestions:read",
    "service:suggestions:enrich",
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "services" in tables:
        service_cols = {c["name"] for c in inspector.get_columns("services")}
        if "granted_scopes" not in service_cols:
            op.add_column("services", sa.Column("granted_scopes", sa.Text(), nullable=True, server_default="[]"))

    if "users" not in tables:
        op.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT,
                auth_provider TEXT NOT NULL DEFAULT 'local',
                oidc_subject TEXT UNIQUE,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at INTEGER DEFAULT (strftime('%s','now'))
            )
            """
        )

    if "roles" not in tables:
        op.execute(
            """
            CREATE TABLE IF NOT EXISTS roles (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                is_system INTEGER NOT NULL DEFAULT 0,
                permissions_json TEXT NOT NULL
            )
            """
        )

    if "user_role_assignments" not in tables:
        op.execute(
            """
            CREATE TABLE IF NOT EXISTS user_role_assignments (
                user_id TEXT NOT NULL,
                role_id INTEGER NOT NULL,
                PRIMARY KEY (user_id, role_id),
                FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE CASCADE
            ) WITHOUT ROWID
            """
        )

    if "user_managed_accounts" not in tables:
        op.execute(
            """
            CREATE TABLE IF NOT EXISTS user_managed_accounts (
                user_id TEXT NOT NULL,
                server_plugin_id INTEGER NOT NULL,
                managed_account_id TEXT NOT NULL,
                PRIMARY KEY (user_id, server_plugin_id, managed_account_id),
                FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
            ) WITHOUT ROWID
            """
        )

    if "api_keys" not in tables:
        op.execute(
            """
            CREATE TABLE IF NOT EXISTS api_keys (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                key_prefix TEXT NOT NULL,
                key_hash TEXT NOT NULL,
                scopes_json TEXT NOT NULL,
                expires_at INTEGER,
                revoked_at INTEGER,
                created_at INTEGER DEFAULT (strftime('%s','now')),
                FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
            )
            """
        )
        op.execute("CREATE INDEX IF NOT EXISTS ix_api_keys_user_id ON api_keys (user_id)")
        op.execute("CREATE INDEX IF NOT EXISTS ix_api_keys_key_prefix ON api_keys (key_prefix)")

    op.execute(
        sa.text(
            "INSERT OR IGNORE INTO roles (name, is_system, permissions_json) "
            "VALUES (:name, 1, :perms)"
        ).bindparams(name="admin", perms=json.dumps(["*"]))
    )
    op.execute(
        sa.text(
            "INSERT OR IGNORE INTO roles (name, is_system, permissions_json) "
            "VALUES (:name, 1, :perms)"
        ).bindparams(name="member", perms=json.dumps(_MEMBER_PERMISSIONS))
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    for table_name in ("api_keys", "user_managed_accounts", "user_role_assignments", "roles", "users"):
        if table_name in tables:
            op.drop_table(table_name)
    if "services" in tables:
        service_cols = {c["name"] for c in inspector.get_columns("services")}
        if "granted_scopes" in service_cols:
            with op.batch_alter_table("services") as batch_op:
                batch_op.drop_column("granted_scopes")
