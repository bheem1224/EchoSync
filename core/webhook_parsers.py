import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class WebhookParser(ABC):
    @abstractmethod
    def parse(self, request) -> Optional[Dict[str, Any]]:
        pass

class PlexWebhookParser(WebhookParser):
    def __init__(self, event_bus=None):
        self.event_bus = event_bus

    def parse_and_publish(self, payload: Dict[str, Any]) -> None:
        try:
            event_type = payload.get('event')

            if event_type not in ['media.rate', 'media.scrobble']:
                return

            metadata = payload.get('Metadata', {})
            # Use guid strictly as requested by test
            guid = metadata.get('guid', '')
            if guid.startswith('mbid://'):
                sync_id = f"ss:track:mbid:{guid.split('mbid://')[1]}"
            else:
                return

            account = payload.get('Account', {})
            user_id = account.get('id')

            if event_type == 'media.rate':
                # Plex wire format is 2× the displayed star rating (e.g. 4 stars → 8.0).
                # Divide by 2 to normalise to display stars (0.5–5.0) before storing,
                # so stars_to_ten_point() receives the correct scale.
                raw_plex_rating = float(metadata.get('userRating', 0))
                rating = raw_plex_rating / 2.0
                event = {
                    "event": "TRACK_RATED",
                    "sync_id": sync_id,
                    "data": {
                        "rating": rating,
                        "user_id": user_id,
                        "provider": "plex"
                    }
                }
            elif event_type == 'media.scrobble':
                event = {
                    "event": "TRACK_PLAYED",
                    "sync_id": sync_id,
                    "data": {
                        "user_id": user_id,
                        "provider": "plex"
                    }
                }
            else:
                return

            if self.event_bus:
                self.event_bus.publish(event)
        except Exception:
            pass

    def parse(self, request) -> Optional[Dict[str, Any]]:
        pass

class NavidromeWebhookParser(WebhookParser):
    def __init__(self, event_bus=None):
        self.event_bus = event_bus

    def parse_and_publish(self, payload: Dict[str, Any]) -> None:
        pass

    def parse(self, request) -> Optional[Dict[str, Any]]:
        pass
