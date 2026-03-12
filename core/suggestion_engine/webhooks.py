"""
Webhook parser interface and implementations for extracting user ratings and play counts
from various media server payloads.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple

from core.tiered_logger import get_logger

logger = get_logger("webhook_parser")

class WebhookParser(ABC):
    @abstractmethod
    def parse_payload(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse the incoming payload and return a standardized dictionary containing:
        - event_type: str ("rate" or "scrobble")
        - source: str
        - user_identifier: str
        - track_title: str
        - artist_name: str
        - rating: Optional[float] (0.0 - 10.0)
        - play_count: Optional[int]
        """
        pass

class PlexWebhookParser(WebhookParser):
    def parse_payload(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        event = payload.get("event")
        metadata = payload.get("Metadata", {})
        account = payload.get("Account", {})

        media_type = metadata.get("type")
        if media_type != "track":
            logger.debug(f"Plex parser ignoring media type: {media_type}")
            return None

        user_identifier = account.get("title")
        if not user_identifier:
            logger.warning("Plex webhook missing Account.title")
            return None

        track_title = metadata.get("title")
        artist_name = metadata.get("grandparentTitle")

        if not track_title or not artist_name:
            logger.warning("Plex webhook missing track or artist metadata")
            return None

        result = {
            "source": "plex",
            "user_identifier": user_identifier,
            "track_title": track_title,
            "artist_name": artist_name,
            "rating": None,
            "play_count": None
        }

        if event == "media.rate":
            rating = metadata.get("userRating")
            if rating is None:
                return None
            result["event_type"] = "rate"
            result["rating"] = float(rating)  # Plex uses 0-10 scale
            return result

        elif event == "media.scrobble":
            result["event_type"] = "scrobble"
            result["play_count"] = 1  # Incremental scrobble
            return result

        return None

class NavidromeWebhookParser(WebhookParser):
    def parse_payload(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # Navidrome webhooks are not currently implemented, but the architecture is ready.
        logger.debug("NavidromeWebhookParser: Not Implemented Yet")
        return None
