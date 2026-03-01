from typing import Any, Dict, Optional

from core.tiered_logger import get_logger

logger = get_logger("oauth_manager")

class OAuthManager:
    """
    Registry for managing OAuth callbacks.
    Providers register themselves here upon initialization so the sidecar can look them up.
    """
    _providers: Dict[str, Any] = {}

    @classmethod
    def register_provider(cls, provider_id: str, provider_instance: Any) -> None:
        """Register a provider instance to handle OAuth callbacks."""
        if provider_id in cls._providers:
            logger.debug(f"Provider '{provider_id}' is already registered for OAuth callbacks. Overwriting.")
        cls._providers[provider_id] = provider_instance
        logger.debug(f"Registered OAuth callback handler for '{provider_id}'")

    @classmethod
    def get_provider(cls, provider_id: str) -> Optional[Any]:
        """Retrieve a registered provider by ID."""
        return cls._providers.get(provider_id)
