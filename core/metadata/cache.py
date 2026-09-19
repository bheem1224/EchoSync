import collections
from typing import Any
from core.tiered_logger import get_logger

logger = get_logger("core.metadata.cache")


class ChromaprintCache:
    """Manages an LRU memory cache and SQLite peer-track lookups for Chromaprints."""

    def __init__(self, max_size: int = 200):
        self.max_size = max_size
        self._cache: collections.OrderedDict[str, dict[str, Any]] = collections.OrderedDict()

    def invalidate(self, chromaprint: str | None = None) -> None:
        """Invalidate in-memory chromaprint cache entry or entire cache."""
        if chromaprint:
            self._cache.pop(chromaprint, None)
        else:
            self._cache.clear()

    def check_local(self, chromaprint: str, sync_id: str | None = None) -> dict[str, Any] | None:
        """Inspect in-memory cache and query music_library.db for peer tracks sharing the chromaprint."""
        if not chromaprint or len(chromaprint.strip()) < 50:
            return None

        if chromaprint in self._cache:
            return self._cache[chromaprint]

        try:
            from database.music_database import (
                AudioFingerprint,
                LocalMedia,
                Track,
                get_database,
            )

            db = get_database()
            with db.session_scope() as session:
                query = (
                    session.query(Track)
                    .join(LocalMedia, LocalMedia.track_id == Track.id)
                    .join(
                        AudioFingerprint,
                        AudioFingerprint.media_id == LocalMedia.media_id,
                    )
                    .filter(
                        AudioFingerprint.chromaprint == chromaprint,
                        Track.musicbrainz_id.isnot(None),
                        Track.musicbrainz_id != "",
                        Track.musicbrainz_id != "NOT_FOUND",
                        Track.title.isnot(None),
                        Track.title != "",
                    )
                )
                if sync_id:
                    query = query.filter(Track.sync_id != sync_id)

                peer_track = query.first()
                if not peer_track:
                    return None

                artist_name = peer_track.artist.name if peer_track.artist else None
                album_title = peer_track.album.title if peer_track.album else None
                release_mbid = peer_track.album.mb_release_id if peer_track.album else None

                res = {
                    "title": peer_track.title,
                    "artist": artist_name,
                    "album": album_title,
                    "year": peer_track.year,
                    "isrc": peer_track.isrc,
                    "musicbrainz_id": peer_track.musicbrainz_id,
                    "musicbrainz_track_id": peer_track.musicbrainz_id,
                    "release_mbid": release_mbid,
                    "track_number": peer_track.track_number,
                    "disc_number": peer_track.disc_number,
                    "duration_ms": peer_track.duration,
                }
                if res:
                    if len(self._cache) >= self.max_size:
                        self._cache.popitem(last=False)
                    self._cache[chromaprint] = res
                return res
        except Exception as exc:
            logger.debug("[cache] Local chromaprint DB lookup failed: %s", exc)
            return None
