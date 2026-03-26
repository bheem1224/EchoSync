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
            if metadata.get('type') != 'track':
                return

            provider_item_id = metadata.get('ratingKey')
            if not provider_item_id:
                return

            provider_item_id = str(provider_item_id)

            # Keep guid parsing for legacy compatibility if available
            guid = metadata.get('guid', '')
            sync_id = None
            if guid.startswith('mbid://'):
                sync_id = f"ss:track:mbid:{guid.split('mbid://')[1]}"

            account = payload.get('Account', {})
            user_id = account.get('id')
            if user_id is not None:
                user_id = str(user_id)

            if event_type == 'media.rate':
                raw_plex_rating = float(metadata.get('userRating', 0))
                rating = raw_plex_rating / 2.0
                event = {
                    "event": "TRACK_RATED",
                    "sync_id": sync_id,  # May be None, that is fine
                    "data": {
                        "rating": rating,
                        "user_id": user_id,
                        "provider": "plex",
                        "provider_item_id": provider_item_id
                    }
                }
            elif event_type == 'media.scrobble':
                event = {
                    "event": "TRACK_PLAYED",
                    "sync_id": sync_id,  # May be None, that is fine
                    "data": {
                        "user_id": user_id,
                        "provider": "plex",
                        "provider_item_id": provider_item_id
                    }
                }
            else:
                return

            if self.event_bus:
                self.event_bus.publish(event)
        except Exception:
            pass

    def parse(self, request) -> Optional[Dict[str, Any]]:
        try:
            if not request.form or 'payload' not in request.form:
                return None

            payload_str = request.form.get('payload')
            if not payload_str:
                return None

            payload = json.loads(payload_str)

            event_type = payload.get('event')
            if event_type != "media.scrobble":
                return None

            metadata = payload.get('Metadata', {})
            if metadata.get('type') != 'track':
                return None

            provider_item_id = metadata.get('ratingKey')
            if not provider_item_id:
                return None

            account = payload.get('Account', {})
            user_id = account.get('id')

            if user_id is None:
                return None

            return {
                "user_id": str(user_id),
                "provider_item_id": str(provider_item_id)
            }
        except Exception:
            return None

class NavidromeWebhookParser(WebhookParser):
    def __init__(self, event_bus=None):
        self.event_bus = event_bus

    def parse_and_publish(self, payload: Dict[str, Any]) -> None:
        pass

    def parse(self, request) -> Optional[Dict[str, Any]]:
        pass


_PROVIDER_PARSERS = {
    "plex": PlexWebhookParser,
    "navidrome": NavidromeWebhookParser,
}


def parse_media_server_webhook(request, provider: str = "plex") -> Optional[Dict[str, Any]]:
    """
    Module-level dispatcher: parse an inbound webhook request from any supported
    media server and return a normalised ``{user_id, provider_item_id}`` dict on
    a ``media.scrobble`` / track event, or ``None`` for unrecognised events.

    Args:
        request: The Flask ``request`` object.
        provider: Lowercase provider name (e.g. ``"plex"``, ``"navidrome"``).

    Returns:
        ``{"user_id": str, "provider_item_id": str}`` or ``None``.
    """
    parser_cls = _PROVIDER_PARSERS.get((provider or "").lower())
    if parser_cls is None:
        return None
    return parser_cls().parse(request)
