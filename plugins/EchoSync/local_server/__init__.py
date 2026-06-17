from .client import LocalServerProvider
from .database_cleanup import register_database_cleanup_job

# Auto-register plugin-specific jobs
try:
    register_database_cleanup_job(enabled=True)
except Exception:
    pass

ProviderClass = LocalServerProvider

__all__ = ['ProviderClass']
