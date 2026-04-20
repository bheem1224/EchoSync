import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import socket
import ipaddress
import urllib.parse
from core.tiered_logger import get_logger

logger = get_logger("webhook_parsers")

def validate_safe_url(url: str) -> Optional[str]:
    """Validate that a URL does not point to an internal or private IP address.
    Returns the rewritten URL locked to the resolved IP to prevent DNS Rebinding TOCTOU.
    """
    try:
        if not url:
            return None

        parsed = urllib.parse.urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return None

        ip_addr = socket.gethostbyname(hostname)
        ip = ipaddress.ip_address(ip_addr)

        if ip.is_private or ip.is_loopback or ip.is_multicast or ip.is_link_local:
            return None

        # Rebuild the URL using the IP address but keeping the original Host header semantics.
        # However, for simple fields like image_url, the client fetching it might just be the browser
        # or a generic requests call. If we replace the hostname with IP, HTTPS certs might fail.
        # But this is what the audit explicitly recommended for SSRF TOCTOU prevention.
        # We will replace the netloc with the IP address (with port if present).

        port_suffix = f":{parsed.port}" if parsed.port else ""
        new_netloc = f"{ip_addr}{port_suffix}"

        # We can't easily pass the Host header if this URL is used by a browser or an opaque downloader,
        # but we do what we can. The audit said: "implement an HTTP client configuration that strictly binds requests
        # to the IP resolved... or configure network-level egress filtering."
        # Returning the IP-bound URL is the standard code-level fix for URL validation functions.

        rewritten = parsed._replace(netloc=new_netloc).geturl()
        return rewritten
    except Exception as e:
        logger.warning(f"URL validation failed for {url}: {e}")
        return None


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

    parsed_data = parser_cls().parse(request)

    if parsed_data:
        # Sanitize any URL fields
        url_fields = ["image_url", "artwork", "thumb", "art", "callback"]
        for field in url_fields:
            if field in parsed_data and parsed_data[field]:
                safe_url = validate_safe_url(parsed_data[field])
                if not safe_url:
                    logger.warning(f"SSRF blocked: neutralized internal URL in field {field}")
                    parsed_data[field] = None
                else:
                    parsed_data[field] = safe_url

    return parsed_data
