"""
Bridge module re-exporting StorageService from services.storage_service.
"""

from services.storage_service import StorageService, get_storage_service

__all__ = ["StorageService", "get_storage_service"]
