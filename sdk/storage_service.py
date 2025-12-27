from __future__ import annotations
from typing import Any, Dict, Optional

from config.settings import config_manager

# Config DB access (secrets/accounts/tokens/PKCE)
try:
    from database.config_database import get_config_database
except Exception:
    get_config_database = None  # Will be available after module is added

# Music library DB (read/write for library entities)
from database.music_database import get_database as get_music_database


class StorageService:
    """Unified storage facade for plugins and providers.
    - Preferences (config.json) via config_manager
    - Secrets/accounts/tokens (config.db) via ConfigDatabase
    - Library entities (music_library.db) via MusicDatabase
    """

    # -------- Preferences (config.json) --------
    def get_pref(self, key: str, default: Any = None) -> Any:
        return config_manager.get(key, default)

    def set_pref(self, key: str, value: Any) -> None:
        # config_manager.set persists non-secrets to config.json and secrets to config.db automatically
        config_manager.set(key, value)

    # -------- Secrets & Accounts (config.db) --------
    @property
    def _cfg(self):
        if get_config_database is None:
            raise RuntimeError("ConfigDatabase not available yet")
        return get_config_database()

    def ensure_service(self, name: str, display_name: Optional[str] = None, service_type: str = 'streaming', description: Optional[str] = None) -> int:
        return self._cfg.register_service(name=name, display_name=display_name or name.capitalize(), service_type=service_type, description=description or f"{name.capitalize()} service")

    def set_service_config(self, service_name: str, key: str, value: Any, is_sensitive: bool = False) -> bool:
        svc_id = self._cfg.get_or_create_service_id(service_name)
        return self._cfg.set_service_config(svc_id, key, value, is_sensitive=is_sensitive)

    def get_service_config(self, service_name: str, key: str) -> Optional[str]:
        svc_id = self._cfg.get_or_create_service_id(service_name)
        return self._cfg.get_service_config(svc_id, key)

    def list_accounts(self, service_name: str) -> list[Dict[str, Any]]:
        svc_id = self._cfg.get_or_create_service_id(service_name)
        return self._cfg.get_accounts(service_id=svc_id)

    def ensure_account(self, service_name: str, account_id: Optional[int] = None, account_name: Optional[str] = None, display_name: Optional[str] = None, user_id: Optional[str] = None) -> int:
        svc_id = self._cfg.get_or_create_service_id(service_name)
        return self._cfg.ensure_account(service_id=svc_id, account_id=account_id, account_name=account_name, display_name=display_name, user_id=user_id)

    def set_active_account(self, service_name: str, account_id: int) -> bool:
        svc_id = self._cfg.get_or_create_service_id(service_name)
        return self._cfg.set_active_account(svc_id, account_id)

    def save_account_token(self, account_id: int, access_token: str, refresh_token: Optional[str] = None, token_type: str = 'Bearer', expires_at: Optional[int] = None, scope: Optional[str] = None) -> bool:
        return self._cfg.save_account_token(account_id, access_token, refresh_token, token_type, expires_at, scope)

    def get_account_token(self, account_id: int) -> Optional[Dict[str, Any]]:
        return self._cfg.get_account_token(account_id)

    def mark_account_authenticated(self, account_id: int) -> bool:
        return self._cfg.mark_account_authenticated(account_id)

    def set_account_user_id(self, account_id: int, user_id: str) -> bool:
        return self._cfg.set_account_user_id(account_id, user_id)

    def delete_account(self, account_id: int) -> bool:
        return self._cfg.delete_account(account_id)

    def update_account_name(self, account_id: int, new_name: str) -> bool:
        return self._cfg.update_account_name(account_id, new_name)

    # PKCE sessions
    def store_pkce_session(self, pkce_id: str, service: str, account_id: int, code_verifier: str, code_challenge: str, redirect_uri: str, client_id: str, ttl_seconds: int = 600) -> bool:
        return self._cfg.store_pkce_session(pkce_id, service, account_id, code_verifier, code_challenge, redirect_uri, client_id, ttl_seconds)

    def get_pkce_session(self, pkce_id: str) -> Optional[Dict[str, Any]]:
        return self._cfg.get_pkce_session(pkce_id)

    def delete_pkce_session(self, pkce_id: str) -> bool:
        return self._cfg.delete_pkce_session(pkce_id)

    def cleanup_expired_pkce_sessions(self) -> None:
        self._cfg.cleanup_expired_pkce_sessions()

    # -------- Library (music_library.db) --------
    @property
    def _lib(self):
        return get_music_database()

    # Expose only read APIs here for plugins; write methods can be added as needed
    def get_library_summary(self) -> Dict[str, int]:
        """Example aggregated counts; extend with concrete queries as needed."""
        db = self._lib
        try:
            with db._get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT COUNT(*) FROM artists"); artists = c.fetchone()[0]
                c.execute("SELECT COUNT(*) FROM albums"); albums = c.fetchone()[0]
                c.execute("SELECT COUNT(*) FROM tracks"); tracks = c.fetchone()[0]
                return {"artists": artists, "albums": albums, "tracks": tracks}
        except Exception:
            return {"artists": 0, "albums": 0, "tracks": 0}


# Singleton accessor
_storage_service: Optional[StorageService] = None

def get_storage_service() -> StorageService:
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
