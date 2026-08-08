import json
import logging
from typing import Any, Dict, Optional
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

        port_suffix = f":{parsed.port}" if parsed.port else ""
        new_netloc = f"{ip_addr}{port_suffix}"

        rewritten = parsed._replace(netloc=new_netloc).geturl()
        return rewritten
    except Exception as e:
        logger.warning(f"URL validation failed for {url}: {e}")
        return None

class WebhookParser:
    def parse_and_publish(self, data: dict) -> None:
        raise NotImplementedError

    def parse(self, data: dict) -> Optional[Dict[str, Any]]:
        raise NotImplementedError


class PlexWebhookParser(WebhookParser):
    def __init__(self, event_bus=None):
        self.event_bus = event_bus

    def parse_and_publish(self, data: dict) -> None:
        pass # Placeholder for event_bus publishing if needed

    def parse(self, data: dict) -> Optional[Dict[str, Any]]:
        try:
            if 'payload' in data:
                payload_str = data.get('payload')
                if isinstance(payload_str, str):
                    payload = json.loads(payload_str)
                else:
                    payload = payload_str
            else:
                payload = data

            if not isinstance(payload, dict):
                return None

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
                "plugin_item_id": str(provider_item_id)
            }
        except Exception:
            return None


class NavidromeWebhookParser(WebhookParser):
    def __init__(self, event_bus=None):
        self.event_bus = event_bus

    def parse_and_publish(self, data: dict) -> None:
        pass

    def parse(self, data: dict) -> Optional[Dict[str, Any]]:
        pass


_PLUGIN_PARSERS = {
    "plex": PlexWebhookParser,
    "navidrome": NavidromeWebhookParser,
}


def parse_media_server_webhook(data: dict, plugin: str = "plex") -> Optional[Dict[str, Any]]:
    """
    Module-level dispatcher: parse an inbound webhook request from any supported
    media server and return a normalised ``{user_id, plugin_item_id}`` dict on
    a ``media.scrobble`` / track event, or ``None`` for unrecognised events.

    Args:
        data: The raw dictionary payload from the webhook request.
        plugin: Lowercase plugin name (e.g. ``"plex"``, ``"navidrome"``).

    Returns:
        ``{"user_id": str, "plugin_item_id": str}`` or ``None``.
    """
    parser_cls = _PLUGIN_PARSERS.get((plugin or "").lower())
    if parser_cls is None:
        return None

    parsed_data = parser_cls().parse(data)

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
