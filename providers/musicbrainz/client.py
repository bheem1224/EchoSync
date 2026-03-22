from typing import List, Optional, Dict, Any
import re

from core.provider_base import ProviderBase
from core.provider import (
    ProviderCapabilities,
    PlaylistSupport,
    SearchCapabilities,
    MetadataRichness,
    ProviderRegistry,
)
from core.request_manager import RateLimitConfig
from core.matching_engine.soul_sync_track import SoulSyncTrack
from core.tiered_logger import get_logger

logger = get_logger("provider.musicbrainz")


class MusicBrainzClient(ProviderBase):
    """Dedicated metadata provider used by discovery and enrichment flows."""

    name = "musicbrainz"
    service_type = "metadata"
    capabilities = ProviderCapabilities(
        name="musicbrainz",
        supports_playlists=PlaylistSupport.NONE,
        search=SearchCapabilities(tracks=True, artists=True, albums=True, playlists=False),
        metadata=MetadataRichness.HIGH,
        supports_cover_art=True,
        supports_lyrics=False,
        supports_user_auth=False,
        supports_library_scan=False,
        supports_streaming=False,
        supports_downloads=False,
        supports_metadata_fetch=True,
    )

    def __init__(self):
        super().__init__()
        self.http.rate = RateLimitConfig(requests_per_second=1.0)
        self.http._session.headers.update(
            {
                "User-Agent": "SoulSync/0.1.0 ( https://github.com/soulsync/soulsync )",
                "Accept": "application/json",
            }
        )
        self.api_base = "https://musicbrainz.org/ws/2"

    def get_artist_tracks(self, artist_name: str) -> List[SoulSyncTrack]:
        """Fetch a full-ish artist tracklist from MusicBrainz recordings search.

        The discovery engine uses SoulSyncTrack.sync_id to diff these results
        against local libraries, so tracks must be created through the standard
        factory path to ensure deterministic IDs.
        """
        artist_name = str(artist_name or "").strip()
        if not artist_name:
            return []

        tracks: List[SoulSyncTrack] = []
        offset = 0
        limit = 100
        max_records = 500

        try:
            while len(tracks) < max_records:
                if re.fullmatch(r"[0-9a-fA-F-]{36}", artist_name):
                    query = f'arid:{artist_name}'
                else:
                    query = f'artist:"{artist_name}"'
                response = self.http.get(
                    f"{self.api_base}/recording",
                    params={
                        "fmt": "json",
                        "query": query,
                        "limit": limit,
                        "offset": offset,
                    },
                )

                if response.status_code != 200:
                    logger.warning(
                        "MusicBrainz get_artist_tracks failed for '%s' (status=%s)",
                        artist_name,
                        response.status_code,
                    )
                    break

                payload = response.json() or {}
                recordings = payload.get("recordings", []) or []
                if not recordings:
                    break

                for recording in recordings:
                    title = str(recording.get("title") or "").strip()
                    if not title:
                        continue

                    artist_credit = recording.get("artist-credit") or []
                    provider_artist = ""
                    for entry in artist_credit:
                        if isinstance(entry, dict):
                            provider_artist += str(entry.get("name") or "")
                            provider_artist += str(entry.get("joinphrase") or "")

                    provider_artist = provider_artist.strip() or artist_name

                    releases = recording.get("releases") or []
                    album_title = ""
                    release_year = None
                    if releases:
                        first_release = releases[0] or {}
                        album_title = str(first_release.get("title") or "")
                        date_value = str(first_release.get("date") or "")
                        if len(date_value) >= 4 and date_value[:4].isdigit():
                            release_year = int(date_value[:4])

                    recording_mbid = str(recording.get("id") or "").strip() or None
                    isrc = None
                    isrc_list = recording.get("isrcs") or []
                    if isrc_list:
                        isrc = str(isrc_list[0] or "").strip() or None

                    track_obj = self.create_soul_sync_track(
                        title=title,
                        artist=provider_artist,
                        album=album_title or "Unknown Album",
                        musicbrainz_id=recording_mbid,
                        isrc=isrc,
                        year=release_year,
                        provider_id=recording_mbid,
                        source=self.name,
                    )
                    if track_obj:
                        tracks.append(track_obj)
                        if len(tracks) >= max_records:
                            break

                if len(recordings) < limit:
                    break
                offset += limit

        except Exception as exc:
            logger.error(f"Failed to fetch artist tracks for '{artist_name}': {exc}", exc_info=True)

        # Deduplicate by base sync identity to keep discovery diff deterministic.
        deduped: Dict[str, SoulSyncTrack] = {}
        for track in tracks:
            deduped[track.sync_id.split("?")[0]] = track

        return list(deduped.values())

    def get_metadata(self, mbid: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed metadata for a recording MBID."""
        mbid = str(mbid or "").strip()
        if not mbid:
            return None

        try:
            response = self.http.get(
                f"{self.api_base}/recording/{mbid}",
                params={"fmt": "json", "inc": "artists+releases+isrcs+media"},
            )
            if response.status_code != 200:
                return None

            data = response.json() or {}
            result = {
                "title": data.get("title"),
                "recording_id": data.get("id"),
                "artist": "",
                "artist_id": "",
                "album": "",
                "release_id": "",
                "date": "",
                "track_number": None,
                "disc_number": None,
                "cover_art_url": None,
                "isrc": None,
            }

            credits = data.get("artist-credit") or []
            if credits:
                name_parts = []
                for credit in credits:
                    if isinstance(credit, dict):
                        name_parts.append(str(credit.get("name") or ""))
                        name_parts.append(str(credit.get("joinphrase") or ""))
                result["artist"] = "".join(name_parts).strip()
                if isinstance(credits[0], dict) and isinstance(credits[0].get("artist"), dict):
                    result["artist_id"] = credits[0]["artist"].get("id") or ""

            releases = data.get("releases") or []
            if releases:
                release = releases[0] or {}
                result["album"] = release.get("title") or ""
                result["release_id"] = release.get("id") or ""
                result["date"] = release.get("date") or ""
                if result["release_id"]:
                    result["cover_art_url"] = self._get_cover_art(result["release_id"])

            isrcs = data.get("isrcs") or []
            if isrcs:
                result["isrc"] = isrcs[0]

            return result

        except Exception as exc:
            logger.error(f"Failed to fetch metadata for {mbid}: {exc}")
            return None

    def _get_cover_art(self, release_id: str) -> Optional[str]:
        try:
            resp = self.http.request(
                "HEAD",
                f"https://coverartarchive.org/release/{release_id}/front",
                allow_redirects=True,
            )
            if resp.status_code == 200:
                return resp.url
        except Exception:
            pass
        return None

    # ProviderBase abstract methods
    def authenticate(self, **kwargs) -> bool:
        return True

    def search(
        self,
        query: str,
        type: str = "track",
        limit: int = 10,
        quality_profile: Optional[Dict[str, Any]] = None,
    ) -> List[SoulSyncTrack]:
        if type != "track":
            return []
        return self.get_artist_tracks(query)[:limit]

    def get_track(self, track_id: str) -> Optional[SoulSyncTrack]:
        metadata = self.get_metadata(track_id)
        if not metadata:
            return None
        return self.create_soul_sync_track(
            title=metadata.get("title") or "",
            artist=metadata.get("artist") or "",
            album=metadata.get("album") or "Unknown Album",
            musicbrainz_id=metadata.get("recording_id"),
            isrc=metadata.get("isrc"),
            provider_id=metadata.get("recording_id"),
            source=self.name,
        )

    def get_album(self, album_id: str) -> Optional[Dict[str, Any]]:
        return None

    def get_artist(self, artist_id: str) -> Optional[Dict[str, Any]]:
        tracks = self.get_artist_tracks(artist_id)
        return {"id": artist_id, "tracks": tracks}

    def get_user_playlists(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return []

    def get_playlist_tracks(self, playlist_id: str) -> List[SoulSyncTrack]:
        return []

    def is_configured(self) -> bool:
        return True

    def get_logo_url(self) -> str:
        return "https://musicbrainz.org/static/images/entity/musicbrainz_logo.svg"


# Backward compatibility alias for older imports.
MusicBrainzProvider = MusicBrainzClient

# Ensure plugin loader/runtime registry can resolve this provider class.
ProviderRegistry.register(MusicBrainzClient)
