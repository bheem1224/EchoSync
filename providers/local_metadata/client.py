from typing import Any, Dict, List, Optional
from core.provider_base import ProviderBase
from core.provider import ProviderCapabilities
from core.enums import Capability
from core.matching_engine.soul_sync_track import SoulSyncTrack


class LocalMetadataProvider(ProviderBase):
    name = 'local_metadata'
    category = 'provider'
    supports_downloads = False
    enabled = True

    capabilities = ProviderCapabilities(
        capabilities=[
            Capability.FETCH_METADATA,
            Capability.TAG_FILES
        ]
    )

    def authenticate(self, **kwargs) -> bool:
        return True

    def search(
        self,
        query: str,
        type: str = "track",
        limit: int = 10,
        quality_profile: Optional[Dict[str, Any]] = None,
    ) -> List[SoulSyncTrack]:
        """Search the local MusicDatabase by title (and optionally artist).

        ``query`` may be a plain title string or an ``"artist - title"``
        compound string.  The function splits on the first " - " if present.
        """
        from database.music_database import get_database

        db = get_database()
        # Support simple "artist - title" compound queries
        artist: Optional[str] = None
        title = query
        if " - " in query:
            parts = query.split(" - ", 1)
            artist, title = parts[0].strip(), parts[1].strip()

        return db.search_canonical_fuzzy(title=title, artist=artist, limit=limit)

    def get_track(self, track_id: str) -> Optional[SoulSyncTrack]:
        """Fetch a single track from the local MusicDatabase by its integer ID."""
        from database.music_database import get_database, Track
        from sqlalchemy.orm import joinedload

        db = get_database()
        try:
            tid = int(track_id)
        except (TypeError, ValueError):
            return None

        with db.session_scope() as session:
            t = (
                session.query(Track)
                .options(joinedload(Track.artist), joinedload(Track.album))
                .filter(Track.id == tid)
                .first()
            )
            if not t:
                return None
            return self.create_soul_sync_track(
                title=t.title,
                artist=t.artist.name if t.artist else "Unknown Artist",
                album=t.album.title if t.album else "",
                duration_ms=t.duration,
                track_number=t.track_number,
                disc_number=t.disc_number,
                bitrate=t.bitrate,
                file_path=t.file_path,
                file_format=t.file_format,
                isrc=t.isrc,
                musicbrainz_id=t.musicbrainz_id,
                provider_id=str(t.id),
                source="local_metadata",
            )

    def get_album(self, album_id: str) -> Optional[Dict[str, Any]]:
        return None

    def get_artist(self, artist_id: str) -> Optional[Dict[str, Any]]:
        return None

    def get_user_playlists(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return []

    def get_playlist_tracks(self, playlist_id: str) -> List[SoulSyncTrack]:
        return []

    def is_configured(self) -> bool:
        return True

    def get_logo_url(self) -> str:
        return ""
