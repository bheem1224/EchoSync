"""
Storage Service module migrated to services/storage_service.py.
Exposes StorageService and get_storage_service() for internal configuration database access.
"""

from typing import Any

from core.settings import config_manager


class StorageService:
    """Helper class exposing a familiar storage API.

    All methods are thin wrappers around ``ConfigManager`` or the
    ``ConfigDatabase`` database layer.
    """

    def __init__(self):
        pass

    # ----- service configuration ------------------------------------------------

    def get_service_config(self, service_name: str, key: str) -> str | None:
        creds = config_manager.get_service_credentials(service_name) or {}
        return creds.get(key)

    def set_service_config(
        self, service_name: str, key: str, value: Any, is_sensitive: bool = False
    ) -> bool:
        try:
            return config_manager.set_service_credentials(
                service_name,
                {key: value},
                sensitive_keys=[key] if is_sensitive else None,
            )
        except Exception as e:
            print(f"[ERROR] set_service_config failed: {e}")
            return False

    def ensure_service(
        self,
        service_name: str,
        service_type: str | None = None,
        description: str | None = None,
    ) -> bool:
        return config_manager.set_service_credentials(service_name, {})

    # ----- account management ---------------------------------------------------

    def list_accounts(self, service_name: str | None = None) -> list[dict[str, Any]]:
        """Return account lists for a given service."""
        from database.config_database import get_config_database

        db = get_config_database()
        service_id = db.get_or_create_service_id(service_name) if service_name else None
        return db.get_accounts(service_id=service_id)

    def ensure_account(
        self,
        service_name: str,
        account_name: str,
        display_name: str | None = None,
        user_id: str | None = None,
    ) -> int | None:
        from database.config_database import get_config_database

        db = get_config_database()
        service_id = db.get_or_create_service_id(service_name)
        return db.ensure_account(
            service_id,
            account_name=account_name,
            display_name=display_name,
            user_id=user_id,
        )

    def upsert_account(
        self,
        service_name: str,
        account_name: str | None = None,
        display_name: str | None = None,
        user_id: str | None = None,
        account_email: str | None = None,
        is_active: bool | None = None,
        is_authenticated: bool | None = None,
        account_id: int | None = None,
    ) -> int | None:
        from database.config_database import get_config_database

        db = get_config_database()
        service_id = db.get_or_create_service_id(service_name)
        return db.upsert_account(
            service_id=service_id,
            account_name=account_name,
            display_name=display_name,
            user_id=user_id,
            account_email=account_email,
            is_active=is_active,
            is_authenticated=is_authenticated,
            account_id=account_id,
        )

    def toggle_account_active(self, account_id: int, active: bool) -> bool:
        from database.config_database import get_config_database

        db = get_config_database()
        return db.toggle_account_active(account_id, active)

    def delete_account(self, account_id: int) -> bool:
        from database.config_database import get_config_database

        db = get_config_database()
        return db.delete_account(account_id)

    def update_account_name(self, account_id: int, new_name: str) -> bool:
        from database.config_database import get_config_database

        db = get_config_database()
        return db.update_account_name(account_id, new_name)

    # ----- token handling -------------------------------------------------------

    def save_account_token(
        self,
        account_id: int,
        access_token: str,
        refresh_token: str | None = None,
        token_type: str = "Bearer",
        expires_at: float | None = None,
        scope: str | None = None,
    ) -> bool:
        try:
            from database.config_database import get_config_database

            db = get_config_database()
            return db.save_account_token(
                account_id, access_token, refresh_token, token_type, expires_at, scope
            )
        except Exception as e:
            print(f"[ERROR] save_account_token failed: {e}")
            return False

    def mark_account_authenticated(self, account_id: int) -> bool:
        try:
            from database.config_database import get_config_database

            db = get_config_database()
            return db.mark_account_authenticated(account_id)
        except Exception as e:
            print(f"[ERROR] mark_account_authenticated failed: {e}")
            return False

    def get_account_token(self, account_id: int) -> dict | None:
        try:
            from database.config_database import get_config_database

            db = get_config_database()
            token = db.get_account_token(account_id)
            if not token:
                return None

            import inspect

            frame = inspect.currentframe()
            try:
                caller_module = inspect.getmodule(frame.f_back)
                caller_name = caller_module.__name__ if caller_module else "unknown"
            finally:
                del frame

            service_name = None
            with db._get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT service_id FROM accounts WHERE id=?", (account_id,))
                row = c.fetchone()
                if row:
                    service_name = db.get_service_name(row[0])

            if service_name and not caller_name.startswith("core."):
                caller_plugin_part = caller_name.removeprefix("plugins.")
                owner_lower = service_name.lower()
                caller_lower = caller_plugin_part.lower()

                if not (
                    caller_lower.startswith(owner_lower)
                    or caller_lower.endswith(f".{owner_lower}")
                    or owner_lower.endswith(f".{caller_lower}")
                ):
                    token["access_token"] = "REDACTED"
                    if token.get("refresh_token"):
                        token["refresh_token"] = "REDACTED"

            return token
        except Exception as e:
            print(f"[ERROR] get_account_token failed: {e}")
            return None

    # ----- per-account configs --------------------------------------------------

    def get_account_config(self, account_id: int, key: str) -> str | None:
        try:
            from database.config_database import get_config_database

            db = get_config_database()
            return db.get_account_config(account_id, key)
        except Exception as e:
            print(f"[ERROR] get_account_config failed: {e}")
            return None

    def set_account_config(
        self, account_id: int, key: str, value: Any, is_sensitive: bool = False
    ) -> bool:
        try:
            from database.config_database import get_config_database

            db = get_config_database()
            return db.set_account_config(
                account_id, key, value, is_sensitive=is_sensitive
            )
        except Exception as e:
            print(f"[ERROR] set_account_config failed: {e}")
            return False

    def delete_account_config(self, account_id: int, key: str) -> bool:
        try:
            from database.config_database import get_config_database

            db = get_config_database()
            return db.delete_account_config(account_id, key)
        except Exception as e:
            print(f"[ERROR] delete_account_config failed: {e}")
            return False

    # ----- PKCE/temporary sessions ---------------------------------------------

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
        try:
            from database.config_database import get_config_database

            db = get_config_database()
            return db.store_pkce_session(
                pkce_id,
                service,
                account_id,
                code_verifier,
                code_challenge,
                redirect_uri,
                client_id,
                ttl_seconds,
            )
        except Exception as e:
            print(f"[ERROR] store_pkce_session failed: {e}")
            return False

    def get_pkce_session(self, pkce_id: str) -> dict[str, Any] | None:
        try:
            from database.config_database import get_config_database

            db = get_config_database()
            return db.get_pkce_session(pkce_id)
        except Exception as e:
            print(f"[ERROR] get_pkce_session failed: {e}")
            return None

    def delete_pkce_session(self, pkce_id: str) -> bool:
        try:
            from database.config_database import get_config_database

            db = get_config_database()
            return db.delete_pkce_session(pkce_id)
        except Exception as e:
            print(f"[ERROR] delete_pkce_session failed: {e}")
            return False

    def cleanup_expired_pkce_sessions(self) -> None:
        try:
            from database.config_database import get_config_database

            db = get_config_database()
            db.cleanup_expired_pkce_sessions()
        except Exception:
            pass

    # ----- database accessors --------------------------------------------------

    def get_working_database(self):
        from database.working_database import get_working_database

        return get_working_database()

    def get_music_database(self):
        from database.music_database import get_database

        return get_database()


_storage_instance: StorageService | None = None


def get_storage_service() -> StorageService:
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = StorageService()
    return _storage_instance
