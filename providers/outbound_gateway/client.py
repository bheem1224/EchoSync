from typing import Any, Dict, List, Optional
from core.provider_base import ProviderBase
from core.enums import Capability
from core.matching_engine.soul_sync_track import SoulSyncTrack

class OutboundGatewayProvider(ProviderBase):
    """
    Outbound Gateway Provider acts as the translator to convert internal
    SoulSyncTrack models into standard, external-friendly JSON schemas for
    the upcoming v2.4/v2.5 API Gateway.
    """
    name = "outbound_gateway"
    category = "provider"
    supports_downloads = False
    enabled = True

    # This provider acts as a proxy/translator and does not have traditional capabilities.
    capabilities = None

    def __init__(self):
        super().__init__()

    def authenticate(self, **kwargs) -> bool:
        """No authentication needed for the outbound translator stub yet."""
        return True

    def is_configured(self) -> bool:
        return True

    def get_logo_url(self) -> str:
        return ""

    def export_track_to_json(self, track: SoulSyncTrack) -> dict:
        """
        Converts a SoulSyncTrack into a standard, external-friendly JSON dictionary.

        Strips out internal SoulSync routing data (sync_id, internal file paths, DB primary keys).
        Formats the output to resemble standard MusicBrainz/ListenBrainz JSON schemas.
        """
        # Expose standard metadata keys, ensuring duration is in seconds
        duration_sec = int(track.duration / 1000) if track.duration else None

        # Build clean JSON schema payload
        payload = {
            "title": track.title,
            "artist": track.artist_name,
            "album": track.album_title,
            "duration": duration_sec,
            "isrc": track.isrc,
            "musicbrainz_id": track.musicbrainz_id,
        }

        # Include additional common metadata if present
        if track.acoustid_id:
            payload["acoustid_id"] = track.acoustid_id
        if track.release_year:
            payload["year"] = track.release_year
        if track.track_number:
            payload["track_number"] = track.track_number
        if track.disc_number:
            payload["disc_number"] = track.disc_number

        # Add remaining external identifiers that are not internal routing keys
        external_identifiers = {}
        for key, value in track.identifiers.items():
            # Filter out any internal identifier schemas if necessary, although
            # standard identifiers in track.identifiers usually resemble provider IDs.
            if key not in ("provider_source", "provider_item_id"):
                external_identifiers[key] = value

        if external_identifiers:
            payload["identifiers"] = external_identifiers

        return payload

    # ==========================================
    # Stubs for ProviderBase abstract methods
    # ==========================================

    def search(
        self,
        query: str,
        type: str = "track",
        limit: int = 10,
        quality_profile: Optional[Dict[str, Any]] = None,
    ) -> List[SoulSyncTrack]:
        return []

    def get_track(self, track_id: str) -> Optional[SoulSyncTrack]:
        return None

    def get_album(self, album_id: str) -> Optional[Dict[str, Any]]:
        return None

    def get_artist(self, artist_id: str) -> Optional[Dict[str, Any]]:
        return None

    def get_user_playlists(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return []

    def get_playlist_tracks(self, playlist_id: str) -> List[SoulSyncTrack]:
        return []
