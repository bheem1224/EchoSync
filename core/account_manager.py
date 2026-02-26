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
        """List all accounts for a service."""
        if service_name == 'spotify':
            return config_manager.get_spotify_accounts()
        elif service_name == 'tidal':
            return config_manager.get_tidal_accounts()
        return []

    @staticmethod
    def get_service_config(service_name: str, key: str) -> Optional[Any]:
        """Get global service configuration."""
        # Special handling for legacy calls
        if service_name == 'spotify':
            return config_manager.get(f'spotify.{key}')
        elif service_name == 'tidal':
            return config_manager.get(f'tidal.{key}')

        # Generic fallback using config_manager.get_service_credentials
        creds = config_manager.get_service_credentials(service_name)
        if key in creds:
            return creds[key]

        # Last resort: config_manager.get
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
