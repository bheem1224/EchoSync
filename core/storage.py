"""
Replacement for the deprecated sdk.storage_service module.

This module exposes a nearly-identical API to the old ``StorageService``
stub that lived in ``sdk/storage_service.py`` but is implemented using the
current ``core.settings.ConfigManager`` and the configuration database
(``database.config_database``) directly.  All existing callers are migrated
here so that the ``sdk`` package can be removed.

New code should *not* depend on this module; instead it should use
:mod:`core.settings` or :mod:`database.config_database` directly.  The
helpers are provided solely to simplify the transition and keep route code
short.

Note that the legacy stub issued a ``DeprecationWarning`` on import; the
replacement is considered the primary API for internal use and therefore
does **not** warn.
"""

from typing import Any, Dict, Iterable, List, Optional
import warnings

from core.settings import config_manager


class StorageService:
    """Helper class exposing a familiar storage API.

    All methods are thin wrappers around ``ConfigManager`` or the
    ``ConfigDatabase`` database layer.  The purpose is to offer a drop-in
    replacement for the old ``sdk.storage_service.StorageService`` so that
    existing code (routes, providers, tests) can be updated with minimal
    changes.
    """

    def __init__(self):
        pass

    # ----- service configuration ------------------------------------------------

    def get_service_config(self, service_name: str, key: str) -> Optional[str]:
        creds = config_manager.get_service_credentials(service_name) or {}
        return creds.get(key)

    def set_service_config(
        self, service_name: str, key: str, value: Any, is_sensitive: bool = False
    ) -> bool:
        try:
            return config_manager.set_service_credentials(
                service_name, {key: value}, sensitive_keys=[key] if is_sensitive else None
            )
        except Exception as e:  # pragma: no cover - very unlikely
            print(f"[ERROR] set_service_config failed: {e}")
            return False

    def ensure_service(
        self,
        service_name: str,
        display_name: Optional[str] = None,
        service_type: Optional[str] = None,
        description: Optional[str] = None,
    ) -> bool:
        # ConfigManager.set_service_credentials will register the service if
        # it doesn't already exist (``register_if_missing`` defaults to True).
        return config_manager.set_service_credentials(service_name, {})

    # ----- account management ---------------------------------------------------

    def list_accounts(self, service_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return account lists for a given service.

        Historically Spotify and Tidal accounts were stored in ``config.json``
        (via :meth:`ConfigManager.get_spotify_accounts`/``get_tidal_accounts``),
        but the modern implementation persists them in the configuration
        database's ``accounts`` table.  Most callers (routes, clients) create
        accounts via :meth:`ensure_account`, which writes to the database, so
        reading from config_manager now returns stale/empty lists.

        To support both legacy and current data we prefer the database when
        possible and fall back to the old config entry only if *no* records are
        found.  This mirrors the behaviour of the original
        ``sdk.storage_service`` stub and keeps tests working.
        """
        # For spotify/tidal try the database first
        if service_name in ('spotify', 'tidal'):
            try:
                from database.config_database import get_config_database
                db = get_config_database()
                service_id = db.get_or_create_service_id(service_name)
                accounts = db.get_accounts(service_id=service_id)
                if accounts:
                    return accounts
            except Exception:
                # ignore and fall back to config manager below
                pass

        # Legacy behaviour: read from config_manager for buckets that still
        # support it.  This is mostly used by a few tests and ensures that
        # existing installations which haven't been migrated continue to work
        # until the UI has had a chance to write the first DB record.
        if service_name == 'spotify':
            return config_manager.get_spotify_accounts()
        if service_name == 'tidal':
            return config_manager.get_tidal_accounts()

        # Generic providers: query the database directly
        from database.config_database import get_config_database

        db = get_config_database()
        service_id = db.get_or_create_service_id(service_name) if service_name else None
        return db.get_accounts(service_id=service_id)

    def ensure_account(
        self,
        service_name: str,
        account_name: str,
        display_name: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Optional[int]:
        if service_name == 'spotify':
            acc = config_manager.add_spotify_account(
                {'account_name': account_name, 'display_name': display_name or account_name, 'user_id': user_id}
            )
            return acc.get('id')
        if service_name == 'tidal':
            # Tidal accounts live in the same place as Spotify accounts
            acc = config_manager.add_tidal_account(
                {'account_name': account_name, 'display_name': display_name or account_name, 'user_id': user_id}
            )
            return acc.get('id')

        from database.config_database import get_config_database
        db = get_config_database()
        service_id = db.get_or_create_service_id(service_name)
        return db.ensure_account(service_id, account_name=account_name, display_name=display_name, user_id=user_id)

    def toggle_account_active(self, account_id: int, active: bool) -> bool:
        # attempt config_manager update for spotify/tidal,
        # otherwise fall back to db toggle
        for name, getter, updater in (
            ('spotify', config_manager.get_spotify_accounts, config_manager.update_spotify_account),
            ('tidal', config_manager.get_tidal_accounts, config_manager.update_tidal_account),
        ):
            accounts = getter() or []
            for acc in accounts:
                if acc.get('id') == account_id:
                    acc = {**acc, 'is_active': bool(active)}
                    updater(account_id, acc)
                    return True

        from database.config_database import get_config_database
        db = get_config_database()
        return db.toggle_account_active(account_id, active)

    def delete_account(self, account_id: int) -> bool:
        # spotify/tidal stored in config_manager
        for getter, deleter in (
            (config_manager.get_spotify_accounts, config_manager.update_spotify_account),
            (config_manager.get_tidal_accounts, config_manager.update_tidal_account),
        ):
            accounts = getter() or []
            if any(acc.get('id') == account_id for acc in accounts):
                new_list = [acc for acc in accounts if acc.get('id') != account_id]
                if getter is config_manager.get_spotify_accounts:
                    config_manager.set('spotify_accounts', new_list)
                else:
                    config_manager.set('tidal_accounts', new_list)
                return True

        # fallback to config database for others
        from database.config_database import get_config_database
        db = get_config_database()
        return db.delete_account(account_id)

    def update_account_name(self, account_id: int, new_name: str) -> bool:
        # try config_manager first
        for getter, updater, key in (
            (config_manager.get_spotify_accounts, config_manager.update_spotify_account, 'spotify_accounts'),
            (config_manager.get_tidal_accounts, config_manager.update_tidal_account, 'tidal_accounts'),
        ):
            accounts = getter() or []
            for acc in accounts:
                if acc.get('id') == account_id:
                    updater(account_id, {'display_name': new_name})
                    return True

        from database.config_database import get_config_database
        db = get_config_database()
        return db.update_account_name(account_id, new_name)

    # ----- token handling -------------------------------------------------------

    def save_account_token(
        self,
        account_id: int,
        access_token: str,
        refresh_token: Optional[str] = None,
        token_type: str = 'Bearer',
        expires_at: Optional[float] = None,
        scope: Optional[str] = None,
    ) -> bool:
        try:
            from database.config_database import get_config_database
            db = get_config_database()
            return db.save_account_token(account_id, access_token, refresh_token, token_type, expires_at, scope)
        except Exception as e:  # pragma: no cover
            print(f"[ERROR] save_account_token failed: {e}")
            return False

    def mark_account_authenticated(self, account_id: int) -> bool:
        try:
            from database.config_database import get_config_database
            db = get_config_database()
            return db.mark_account_authenticated(account_id)
        except Exception as e:  # pragma: no cover
            print(f"[ERROR] mark_account_authenticated failed: {e}")
            return False

    def get_account_token(self, account_id: int) -> Optional[dict]:
        try:
            from database.config_database import get_config_database
            db = get_config_database()
            return db.get_account_token(account_id)
        except Exception as e:  # pragma: no cover
            print(f"[ERROR] get_account_token failed: {e}")
            return None

    # ----- per-account configs --------------------------------------------------

    def get_account_config(self, account_id: int, key: str) -> Optional[str]:
        try:
            from database.config_database import get_config_database
            db = get_config_database()
            return db.get_account_config(account_id, key)
        except Exception as e:  # pragma: no cover
            print(f"[ERROR] get_account_config failed: {e}")
            return None

    def set_account_config(
        self, account_id: int, key: str, value: Any, is_sensitive: bool = False
    ) -> bool:
        try:
            from database.config_database import get_config_database
            db = get_config_database()
            return db.set_account_config(account_id, key, value, is_sensitive=is_sensitive)
        except Exception as e:  # pragma: no cover
            print(f"[ERROR] set_account_config failed: {e}")
            return False

    def delete_account_config(self, account_id: int, key: str) -> bool:
        try:
            from database.config_database import get_config_database
            db = get_config_database()
            return db.delete_account_config(account_id, key)
        except Exception as e:  # pragma: no cover
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
            return db.store_pkce_session(pkce_id, service, account_id, code_verifier, code_challenge, redirect_uri, client_id, ttl_seconds)
        except Exception as e:  # pragma: no cover
            print(f"[ERROR] store_pkce_session failed: {e}")
            return False

    def get_pkce_session(self, pkce_id: str) -> Optional[Dict[str, Any]]:
        try:
            from database.config_database import get_config_database
            db = get_config_database()
            return db.get_pkce_session(pkce_id)
        except Exception as e:  # pragma: no cover
            print(f"[ERROR] get_pkce_session failed: {e}")
            return None

    def delete_pkce_session(self, pkce_id: str) -> bool:
        try:
            from database.config_database import get_config_database
            db = get_config_database()
            return db.delete_pkce_session(pkce_id)
        except Exception as e:  # pragma: no cover
            print(f"[ERROR] delete_pkce_session failed: {e}")
            return False

    def cleanup_expired_pkce_sessions(self) -> None:
        try:
            from database.config_database import get_config_database
            db = get_config_database()
            db.cleanup_expired_pkce_sessions()
        except Exception:  # pragma: no cover
            pass


# global singleton -------------------------------------------------------------
_storage_instance: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = StorageService()
    return _storage_instance
