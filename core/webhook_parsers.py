import ipaddress
import json
import socket
import urllib.parse
from typing import Any

from core.tiered_logger import get_logger

logger = get_logger("webhook_parsers")


def validate_safe_url(url: str) -> str | None:
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

    def parse(self, data: dict) -> dict[str, Any] | None:
        raise NotImplementedError


class PlexWebhookParser(WebhookParser):
    def __init__(self, event_bus=None):
        self.event_bus = event_bus

    def parse_and_publish(self, data: dict) -> None:
        try:
            if "payload" in data:
                payload_str = data.get("payload")
                if isinstance(payload_str, str):
                    payload = json.loads(payload_str)
                else:
                    payload = payload_str
            else:
                payload = data

            if not isinstance(payload, dict):
                return

            event_type = payload.get("event")
            if event_type == "media.rate":
                metadata = payload.get("Metadata", {})
                rating_key = str(metadata.get("ratingKey", ""))
                user_rating = metadata.get("userRating")
                account = payload.get("Account", {})
                account_id = str(account.get("id", ""))
                guid = metadata.get("guid", "")
                mbid = guid.replace("mbid://", "").strip() if "mbid://" in guid else ""
                sync_id = (
                    f"ss:track:mbid:{mbid}" if mbid else f"ss:track:plex:{rating_key}"
                )
                rating = float(user_rating) / 2.0 if user_rating is not None else 0.0
                publish_payload = {
                    "event": "TRACK_RATED",
                    "sync_id": sync_id,
                    "data": {
                        "rating": rating,
                        "account_id": account_id,
                        "plugin_item_id": rating_key,
                    },
                }
                if self.event_bus and hasattr(self.event_bus, "publish"):
                    self.event_bus.publish(publish_payload)
            elif event_type == "media.scrobble":
                parsed = self.parse(data)
                if parsed and self.event_bus and hasattr(self.event_bus, "publish"):
                    self.event_bus.publish(
                        {
                            "event": "TRACK_PLAYED",
                            "sync_id": f"ss:track:plex:{parsed.get('plugin_item_id')}",
                            "data": parsed,
                        }
                    )
        except Exception as e:
            logger.error(f"Error in PlexWebhookParser.parse_and_publish: {e}")

    def parse(self, data: dict) -> dict[str, Any] | None:
        try:
            if "payload" in data:
                payload_str = data.get("payload")
                if isinstance(payload_str, str):
                    payload = json.loads(payload_str)
                else:
                    payload = payload_str
            else:
                payload = data

            if not isinstance(payload, dict):
                return None

            event_type = payload.get("event")
            if event_type != "media.scrobble":
                return None

            metadata = payload.get("Metadata", {})
            if metadata.get("type") != "track":
                return None

            provider_item_id = metadata.get("ratingKey")
            if not provider_item_id:
                return None

            account = payload.get("Account", {})
            user_id = account.get("id")

            if user_id is None:
                return None

            return {"user_id": str(user_id), "plugin_item_id": str(provider_item_id)}
        except Exception:
            return None


class NavidromeWebhookParser(WebhookParser):
    def __init__(self, event_bus=None):
        self.event_bus = event_bus

    def parse_and_publish(self, data: dict) -> None:
        pass

    def parse(self, data: dict) -> dict[str, Any] | None:
        pass


_PLUGIN_PARSERS = {
    "plex": PlexWebhookParser,
    "navidrome": NavidromeWebhookParser,
}


def parse_media_server_webhook(
    data: dict, plugin: str = "plex"
) -> dict[str, Any] | None:
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
            if parsed_data.get(field):
                safe_url = validate_safe_url(parsed_data[field])
                if not safe_url:
                    logger.warning(
                        f"SSRF blocked: neutralized internal URL in field {field}"
                    )
                    parsed_data[field] = None
                else:
                    parsed_data[field] = safe_url

    return parsed_data
