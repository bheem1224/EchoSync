#!/usr/bin/env python3

"""
Wishlist Service - High-level service for managing failed download track wishlist
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from core.matching_engine.matching_engine import WeightedMatchingEngine
from core.job_queue import JobQueue
from utils.logging_config import get_logger

logger = get_logger("wishlist_service")

class WishlistService:
    """Service for managing the wishlist of failed download tracks"""
    
    def __init__(self, database_service, matching_engine: WeightedMatchingEngine, job_queue: JobQueue):
        self.database_service = database_service
        self.matching_engine = matching_engine
        self.job_queue = job_queue
    
    def add_failed_track(self, track_info, source_type="unknown", source_context=None):
        """
        Add a failed track to the wishlist and schedule a retry.
        
        Args:
            track_info: Track info dictionary.
            source_type: Type of source ('playlist', 'album', 'manual').
            source_context: Additional context (e.g., playlist name).
        """
        try:
            normalized_track = self.matching_engine.normalize_track(track_info)
            self.database_service.add_to_wishlist(
                normalized_track,
                failure_reason=track_info.get('failure_reason', 'Download failed'),
                source_type=source_type,
                source_context=source_context or {}
            )

            # Schedule a retry using JobQueue
            self.job_queue.schedule_job(
                name=f"retry_download_{normalized_track['id']}",
                func=self.retry_download,
                args=(normalized_track,),
                delay_seconds=300  # Retry after 5 minutes
            )
            return True
        except Exception as e:
            logger.error(f"Error adding failed track to wishlist: {e}")
            return False

    def retry_download(self, track):
        """Retry downloading a track."""
        try:
            # Logic to retry download
            logger.info(f"Retrying download for track: {track['name']}")
            # ...
        except Exception as e:
            logger.error(f"Error retrying download for track {track['name']}: {e}")

    def get_wishlist_tracks(self, limit=None):
        """
        Retrieve wishlist tracks for display or processing.
        
        Args:
            limit: Maximum number of tracks to retrieve.
        """
        return self.database_service.get_wishlist_tracks(limit=limit)