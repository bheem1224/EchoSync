"""Wrapper for config_database - ensures clean separation and easier debugging."""

from typing import Any

from database.config_database import ConfigDatabase


class ConfigDatabaseWrapper:
    """Wrapper around ConfigDatabase for web module access."""

    def __init__(self, db_path: str | None = None):
        self._db = ConfigDatabase(db_path)

    # === Service Management ===
    def get_or_create_service_id(self, name: str) -> int:
        return self._db.get_or_create_service_id(name)

    def register_service(
        self,
        name: str,
        service_type: str,
        description: str,
        plugin_id: int | None = None,
        version: str | None = None,
    ) -> int:
        return self._db.register_service(
            name=name,
            service_type=service_type,
            description=description,
            plugin_id=plugin_id,
            version=version,
        )

    def set_service_config(
        self, service_id: int, key: str, value: Any, is_sensitive: bool = False
    ) -> bool:
        return self._db.set_service_config(service_id, key, value, is_sensitive)

    def get_service_config(self, service_id: int, key: str) -> str | None:
        return self._db.get_service_config(service_id, key)

    # === Account Management ===
    def get_accounts(
        self, service_id: int | None = None, is_active: bool | None = None
    ) -> list[dict[str, Any]]:
        return self._db.get_accounts(service_id, is_active)

    def ensure_account(
        self,
        service_id: int,
        account_id: int | None = None,
        account_name: str | None = None,
        display_name: str | None = None,
        user_id: str | None = None,
    ) -> int:
        return self._db.ensure_account(
            service_id, account_id, account_name, display_name, user_id
        )

    def set_active_account(self, service_id: int, account_id: int) -> bool:
        return self._db.set_active_account(service_id, account_id)

    def mark_account_authenticated(self, account_id: int) -> bool:
        return self._db.mark_account_authenticated(account_id)

    def set_account_user_id(self, account_id: int, user_id: str) -> bool:
        return self._db.set_account_user_id(account_id, user_id)

    def delete_account(self, account_id: int) -> bool:
        return self._db.delete_account(account_id)

    def update_account_name(self, account_id: int, new_name: str) -> bool:
        return self._db.update_account_name(account_id, new_name)

    # === Token Management ===
    def save_account_token(
        self,
        account_id: int,
        access_token: str,
        refresh_token: str | None = None,
        token_type: str = "Bearer",
        expires_at: int | None = None,
        scope: str | None = None,
    ) -> bool:
        return self._db.save_account_token(
            account_id, access_token, refresh_token, token_type, expires_at, scope
        )

    def get_account_token(self, account_id: int) -> dict[str, Any] | None:
        return self._db.get_account_token(account_id)

    # === PKCE Session Management ===
    def store_pkce_session(
        self,
        pkce_id: str,
        service: str,
        account_id: int,
        code_verifier: str,
        code_challenge: str,
        redirect_uri: str,
        client_id: str,
        ttl_seconds: int = 600,
    ) -> bool:
        return self._db.store_pkce_session(
            pkce_id,
            service,
            account_id,
            code_verifier,
            code_challenge,
            redirect_uri,
            client_id,
            ttl_seconds,
        )

    def get_pkce_session(self, pkce_id: str) -> dict[str, Any] | None:
        return self._db.get_pkce_session(pkce_id)

    def delete_pkce_session(self, pkce_id: str) -> bool:
        return self._db.delete_pkce_session(pkce_id)

    def cleanup_expired_pkce_sessions(self) -> None:
        return self._db.cleanup_expired_pkce_sessions()


import threading

# Singleton instance for app-wide use
_instance: ConfigDatabaseWrapper | None = None
_instance_lock = threading.Lock()


def get_config_database() -> ConfigDatabaseWrapper:
    """Get or create the singleton wrapper instance."""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = ConfigDatabaseWrapper()
    return _instance


def get_config_db() -> ConfigDatabaseWrapper:
    """Alias for FastAPI Depends provider."""
    return get_config_database()
