from typing import Optional, Dict, Any
from core.settings import config_manager
from core.tiered_logger import get_logger

logger = get_logger("account_manager")

class AccountManager:
    """
    Helper class to manage provider account tokens and credentials using the unified ConfigManager.
    This replaces the legacy sdk.storage_service.
    """

    @staticmethod
    def get_account_token(service_name: str, account_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve token data for a specific account."""
        if service_name == 'spotify':
            accounts = config_manager.get_spotify_accounts()
        elif service_name == 'tidal':
            accounts = config_manager.get_tidal_accounts()
        else:
            logger.warning(f"Unsupported service for account token retrieval: {service_name}")
            return None

        for acc in accounts:
            if acc.get('id') == account_id:
                return {
                    'access_token': acc.get('access_token'),
                    'refresh_token': acc.get('refresh_token'),
                    'expires_at': acc.get('expires_at'),
                    'scope': acc.get('scope'),
                    'token_type': acc.get('token_type', 'Bearer')
                }
        return None

    @staticmethod
    def save_account_token(service_name: str, account_id: int, token_info: Dict[str, Any]) -> bool:
        """Save updated token information for an account."""
        if service_name == 'spotify':
            return bool(config_manager.update_spotify_account(account_id, token_info))
        elif service_name == 'tidal':
            return bool(config_manager.update_tidal_account(account_id, token_info))
        else:
            logger.warning(f"Unsupported service for account token storage: {service_name}")
            return False

    @staticmethod
    def list_accounts(service_name: str) -> list:
        """List all accounts for a service.

        Work against the database when available; fall back to the legacy
        ``ConfigManager`` lists only if no rows exist.  This ensures web route
        code can continue calling :func:`core.storage.list_accounts` which uses
        the same logic.
        """
        # try the database first for the two multi-account services
        if service_name in ('spotify', 'tidal'):
            try:
                from database.config_database import get_config_database
                db = get_config_database()
                service_id = db.get_or_create_service_id(service_name)
                accounts = db.get_accounts(service_id=service_id)
                if accounts:
                    return accounts
            except Exception:
                pass

        # legacy fallback
        if service_name == 'spotify':
            return config_manager.get_spotify_accounts()
        elif service_name == 'tidal':
            return config_manager.get_tidal_accounts()
        return []

    @staticmethod
    def get_service_config(service_name: str, key: str) -> Optional[Any]:
        """Get global service configuration.

        Modern credentials are stored in the encrypted *service_config* table and
        exposed through :meth:`ConfigManager.get_service_credentials`.  Legacy
        single‑account settings (e.g. ``spotify.client_id``) lived in the
        in‑memory ``config_data`` dictionary and are accessible via
        :meth:`ConfigManager.get`.

        The previous implementation special‑cased ``spotify`` and ``tidal`` by
        always reading through ``config_manager.get``, which meant that any
        values saved with ``set_service_credentials`` (the UI path) were not
        visible.  That’s why the web UI showed empty fields even though the
        database contained valid entries.

        To fix it we now always try the service_credentials first and fall back
        to the legacy path only if nothing is found.  This keeps backwards
        compatibility while ensuring the database values are picked up.
        """
        # Attempt to retrieve from the modern service_config table first
        creds = config_manager.get_service_credentials(service_name) or {}
        if key in creds:
            return creds[key]

        # Legacy fallback (stored in config_data)
        return config_manager.get(f'{service_name}.{key}')

    @staticmethod
    def get_account(service_name: str, account_id: int) -> Optional[Dict[str, Any]]:
        """Get full account details."""
        accounts = AccountManager.list_accounts(service_name)
        for acc in accounts:
            if acc.get('id') == account_id:
                return acc
        return None

    @staticmethod
    def update_account(service_name: str, account_id: int, updates: Dict[str, Any]) -> bool:
        """Update generic account fields."""
        if service_name == 'spotify':
            return bool(config_manager.update_spotify_account(account_id, updates))
        elif service_name == 'tidal':
            return bool(config_manager.update_tidal_account(account_id, updates))
        return False
