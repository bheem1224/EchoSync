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

    def check_local(
        self,
        chromaprint: str,
        duration_ms: int | None = None,
        sync_id: str | None = None,
        similarity_threshold: float = 0.85,
    ) -> dict[str, Any] | None:
        """Inspect in-memory LRU cache and query music_library.db via duration-bucketed Hamming search."""
        # Support legacy positional call check_local(chromaprint, sync_id)
        if isinstance(duration_ms, str) and sync_id is None:
            sync_id = duration_ms
            duration_ms = None

        fp = chromaprint.strip() if isinstance(chromaprint, str) else ""
        if not fp or len(fp) < 50:
            return None

        cached = self._cache.get(fp)
        if cached is not None:
            if (sync_id is None or cached.get("matched_sync_id") != sync_id) and cached.get(
                "similarity_score", 1.0
            ) >= similarity_threshold:
                self._cache.move_to_end(fp)
                return cached

        try:
            import echosync_core
            from sqlalchemy import and_, or_

            from database.music_database import (
                AudioFingerprint,
                LocalMedia,
                Track,
                get_database,
            )

            db = get_database()
            with db.session_scope() as session:
                base_filters = [
                    Track.verification_tier != "quarantined",
                    Track.musicbrainz_id.isnot(None),
                    Track.musicbrainz_id != "",
                    Track.musicbrainz_id != "NOT_FOUND",
                    Track.title.isnot(None),
                    Track.title != "",
                ]
                if sync_id:
                    base_filters.append(Track.sync_id != sync_id)

                # 1. Fast indexed exact Chromaprint match
                exact_row = (
                    session.query(Track, LocalMedia)
                    .join(LocalMedia, LocalMedia.track_id == Track.id)
                    .join(AudioFingerprint, AudioFingerprint.media_id == LocalMedia.media_id)
                    .filter(AudioFingerprint.chromaprint == fp, *base_filters)
                    .first()
                )

                peer_track = None
                peer_media = None
                similarity_score = 0.0

                if exact_row is not None:
                    peer_track, peer_media = exact_row
                    similarity_score = 1.0
                else:
                    # 2. Duration-bucketed parallel Hamming similarity scan via Rust echosync_core
                    cand_query = (
                        session.query(Track, LocalMedia, AudioFingerprint)
                        .join(LocalMedia, LocalMedia.track_id == Track.id)
                        .join(AudioFingerprint, AudioFingerprint.media_id == LocalMedia.media_id)
                        .filter(
                            AudioFingerprint.chromaprint.isnot(None),
                            AudioFingerprint.chromaprint != "",
                            *base_filters,
                        )
                    )
                    if duration_ms is not None and duration_ms > 0:
                        tolerance_ms = 3000
                        cand_query = cand_query.filter(
                            or_(
                                LocalMedia.duration_ms.between(duration_ms - tolerance_ms, duration_ms + tolerance_ms),
                                and_(
                                    LocalMedia.duration_ms.is_(None),
                                    Track.duration.between(duration_ms - tolerance_ms, duration_ms + tolerance_ms),
                                ),
                            )
                        )

                    candidate_rows = cand_query.all()
                    if candidate_rows:
                        candidates_payload: list[tuple[str, str]] = []
                        candidate_lookup: dict[str, tuple[Any, Any]] = {}
                        for cand_track, cand_media, cand_af in candidate_rows:
                            key = str(cand_af.id)
                            candidates_payload.append((key, str(cand_af.chromaprint)))
                            candidate_lookup[key] = (cand_track, cand_media)

                        best_match = echosync_core.find_best_chromaprint_match(
                            fp,
                            candidates_payload,
                            min_similarity=float(similarity_threshold),
                        )
                        if best_match is not None:
                            best_id, similarity_score = best_match
                            peer_track, peer_media = candidate_lookup[best_id]

                if peer_track is None:
                    return None

                artist_name = peer_track.artist.name if peer_track.artist else None
                album_title = peer_track.album.title if peer_track.album else None
                release_mbid = peer_track.album.mb_release_id if peer_track.album else None
                resolved_duration_ms = (
                    peer_media.duration_ms
                    if peer_media is not None and peer_media.duration_ms is not None
                    else peer_track.duration
                )

                rel_date = (
                    (peer_track.album.original_release_date or peer_track.album.release_date)
                    if peer_track.album is not None
                    else None
                )
                resolved_year = getattr(peer_track, "year", None)
                if resolved_year is None and rel_date is not None:
                    resolved_year = rel_date.year if hasattr(rel_date, "year") else None

                res = {
                    "title": peer_track.title,
                    "artist": artist_name,
                    "album": album_title,
                    "year": resolved_year,
                    "isrc": peer_track.isrc,
                    "musicbrainz_id": peer_track.musicbrainz_id,
                    "musicbrainz_track_id": peer_track.musicbrainz_id,
                    "canonical_mbid": peer_track.canonical_mbid,
                    "release_mbid": release_mbid,
                    "track_number": peer_track.track_number,
                    "disc_number": peer_track.disc_number,
                    "duration_ms": resolved_duration_ms,
                    "matched_track_id": peer_track.id,
                    "matched_sync_id": peer_track.sync_id,
                    "version_type": getattr(peer_track, "version_type", None) or "original",
                    "similarity_score": float(similarity_score),
                }
                if len(self._cache) >= self.max_size:
                    self._cache.popitem(last=False)
                self._cache[fp] = res
                return res
        except Exception as exc:
            logger.debug("[cache] Local chromaprint DB lookup failed: %s", exc)
            return None
