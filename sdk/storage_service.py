"""
SDK Storage Service - DEPRECATED STUB

This module is a stub for backward compatibility only.
All code should use core.settings.config_manager instead.

This stub redirects common calls to config_manager or database.
"""

from typing import Optional
import warnings

warnings.warn(
    "sdk.storage_service is deprecated. Use core.settings.config_manager instead.",
    DeprecationWarning,
    stacklevel=2
)

from core.settings import config_manager


class StorageService:
    """Deprecated stub that redirects to config_manager."""
    
    def __init__(self):
        """Initialize stub storage service."""
        pass
    
    def get_service_config(self, service_name: str, key: str) -> Optional[str]:
        """Get service configuration - redirects to config_manager."""
        creds = config_manager.get_service_credentials(service_name)
        return creds.get(key) if creds else None
    
    def set_service_config(self, service_name: str, key: str, value: str, is_sensitive: bool = False) -> bool:
        """Set service configuration - redirects to config_manager."""
        try:
            credentials = {key: value}
            return config_manager.set_service_credentials(service_name, credentials)
        except Exception as e:
            print(f"[ERROR] set_service_config failed: {e}")
            return False
    
    def ensure_service(self, service_name: str, display_name: Optional[str] = None, service_type: Optional[str] = None, description: Optional[str] = None) -> bool:
        """Ensure service exists - no-op for compatibility."""
        # This is typically a database operation that we don't need to stub
        return True
    
    def get_music_database(self):
        """Get music database - returns database instance."""
        from database import get_database
        return get_database()
    
    def ensure_account(self, service_name: str, account_name: str, display_name: Optional[str] = None, user_id: Optional[str] = None) -> Optional[int]:
        """Ensure account exists - redirects to config_database."""
        try:
            from database.config_database import get_config_database
            db = get_config_database()
            service_id = db.get_or_create_service_id(service_name)
            return db.ensure_account(service_id, account_name=account_name, display_name=display_name, user_id=user_id)
        except Exception as e:
            print(f"[ERROR] ensure_account failed: {e}")
            return None
    
    def save_account_token(self, account_id: int, access_token: str, refresh_token: Optional[str] = None, 
                          token_type: str = 'Bearer', expires_at: Optional[float] = None, 
                          scope: Optional[str] = None) -> bool:
        """Save account token - redirects to database."""
        try:
            from database import get_database
            db = get_database()
            if hasattr(db, 'save_account_token'):
                return db.save_account_token(account_id, access_token, refresh_token, token_type, expires_at, scope)
            return True
        except Exception as e:
            print(f"[ERROR] save_account_token failed: {e}")
            return False
    
    def mark_account_authenticated(self, account_id: int) -> bool:
        """Mark account as authenticated - redirects to database."""
        try:
            from database import get_database
            db = get_database()
            if hasattr(db, 'mark_account_authenticated'):
                return db.mark_account_authenticated(account_id)
            return True
        except Exception as e:
            print(f"[ERROR] mark_account_authenticated failed: {e}")
            return False
    
    def toggle_account_active(self, account_id: int, active: bool) -> bool:
        """Toggle account active status - redirects to database."""
        try:
            from database import get_database
            db = get_database()
            if hasattr(db, 'toggle_account_active'):
                return db.toggle_account_active(account_id, active)
            return True
        except Exception as e:
            print(f"[ERROR] toggle_account_active failed: {e}")
            return False
    
    def list_accounts(self, service_name: Optional[str] = None) -> list:
        """List all accounts or accounts for a specific service."""
        try:
            from database.config_database import get_config_database
            config_db = get_config_database()

            service_id = None
            if service_name:
                service_id = config_db.get_or_create_service_id(service_name)

            return config_db.get_accounts(service_id=service_id)
        except Exception as e:
            print(f"[ERROR] list_accounts failed: {e}")
            return []


# Global singleton instance
_storage_instance: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Get global StorageService instance."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = StorageService()
    return _storage_instance
