from typing import Any

from core.db.echo_sync_track import EchosyncTrack
from core.nexus_framework.plugin_SDK import (
    MetadataRichness,
    PlaylistSupport,
    PluginBase,
    ProviderCapabilities,
    SearchCapabilities,
)


class LocalMetadataProvider(PluginBase):
    name = "EchoSync.local_metadata"
    category = "provider"
    supports_downloads = False
    enabled = True

    capabilities = ProviderCapabilities(
        name="EchoSync.local_metadata",
        supports_playlists=PlaylistSupport.NONE,
        search=SearchCapabilities(tracks=False, albums=False, artists=False),
        metadata=MetadataRichness.MEDIUM,
        supports_metadata_fetch=True,
    )

    def authenticate(self, **kwargs) -> bool:
        return True

    def search(
        self,
        query: str,
        type: str = "track",
        limit: int = 10,
        quality_profile: dict[str, Any] | None = None,
    ) -> list[EchosyncTrack]:
        """Search the local MusicDatabase by title (and optionally artist) via sdk.library."""
        artist: str | None = None
        title = query
        if " - " in query:
            parts = query.split(" - ", 1)
            artist, title = parts[0].strip(), parts[1].strip()

        return self.sdk.library.search_fuzzy(title=title, artist=artist, limit=limit)

    def get_track(self, track_id: str) -> EchosyncTrack | None:
        """Fetch a single track from the local MusicDatabase by its integer ID via sdk.library."""
        record = self.sdk.library.get_track_record_by_id(track_id)
        if not record:
            return None
        return self.create_echo_sync_track(
            title=record["title"],
            artist=record["artist"],
            album=record["album"],
            duration_ms=record["duration_ms"],
            track_number=record["track_number"],
            disc_number=record["disc_number"],
            bitrate=record["bitrate"],
            file_path=record["file_path"],
            file_format=record["file_format"],
            isrc=record["isrc"],
            musicbrainz_id=record["musicbrainz_id"],
            provider_id=str(record["id"]),
            source="EchoSync.local_metadata",
        )

    def get_album(self, album_id: str) -> dict[str, Any] | None:
        return None

    def get_artist(self, artist_id: str) -> dict[str, Any] | None:
        return None

    def get_user_playlists(self, user_id: str | None = None) -> list[dict[str, Any]]:
        return []

    def get_playlist_tracks(self, playlist_id: str) -> list[EchosyncTrack]:
        return []

    def is_configured(self) -> bool:
        return True

    def get_logo_url(self) -> str:
        return ""

    def get_track_from_file(self, file_path: str) -> EchosyncTrack | None:
        """Read physical tags of an audio file and return an EchosyncTrack."""
        from pathlib import Path

        from core.file_handling.tagging_io import read_tags

        try:
            tags = read_tags(Path(file_path))
            if not tags:
                return None

            title = tags.get("title")
            artist = tags.get("artist")

            # Require at least title or artist to consider tags present
            if not title and not artist:
                return None

            return self.create_echo_sync_track(
                title=title or "",
                artist=artist or "",
                album=tags.get("album") or "",
                duration_ms=tags.get("duration"),
                isrc=tags.get("isrc"),
                musicbrainz_id=tags.get("musicbrainz_id") or tags.get("recording_id"),
                mb_release_id=tags.get("release_id") or tags.get("musicbrainz_albumid"),
                acoustid_id=tags.get("acoustid_id") or tags.get("acoustid id"),
                year=tags.get("year") or tags.get("date"),
                track_number=tags.get("track_number") or tags.get("tracknumber"),
                disc_number=tags.get("disc_number") or tags.get("discnumber"),
                bitrate=tags.get("bitrate_kbps") or tags.get("bitrate"),
                sample_rate=tags.get("sample_rate_hz") or tags.get("sample_rate"),
                bit_depth=tags.get("bit_depth"),
                file_format=tags.get("file_format"),
                file_path=file_path,
                source="EchoSync.local_metadata",
            )
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(
                f"Error reading tags via local_metadata for {file_path}: {e}"
            )
            return None
