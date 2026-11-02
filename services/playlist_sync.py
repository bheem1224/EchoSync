#!/usr/bin/env python3
"""
Playlist Sync Service.

Provides decoupled candidate matching (matching ANY local format in library,
selecting highest quality media file, without gating by target_quality)
and persistent match trace caching for 100% diagnostic parity.
"""

import logging
import re
import time
from typing import Any

from sqlalchemy import or_, text
from sqlalchemy.orm import Session, joinedload

from core.db.echo_sync_track import EchosyncTrack
from core.hook_manager import hook_manager
from core.matching_engine.matching_engine import MatchResult, WeightedMatchingEngine
from core.matching_engine.scoring_profile import ExactSyncProfile
from core.matching_engine.text_utils import (
    _cmp_artists,
    _cmp_titles,
    normalize_title as _normalize_candidate_title,
    parse_duration_to_ms,
)
from core.tiered_logger import get_logger
import database.music_database as db_mod
from database.music_database import Album, Artist, LocalMedia, Track, TrackArtist
from services.playlists_api import (
    check_cover_rejection,
    check_title_recovery,
    resolve_duplicate_matches,
)

logger = get_logger("playlist_sync")

LOSSLESS_FORMATS = {"flac", "wav", "alac", "aiff", "dsd", "dff"}

# In-memory match trace cache for diagnostic parity
MATCH_TRACE_CACHE: dict[tuple, dict] = {}


def get_cache_key(
    title: str, artist: str, duration_ms: int = 0, album: str | None = None
) -> tuple[str, str, int]:
    """Derive deterministic cache key for a track query."""
    return (
        (title or "").strip().lower(),
        (artist or "").strip().lower(),
        int(duration_ms or 0),
    )


def cache_match_trace(query_dict: dict, trace: dict) -> None:
    """Store match evaluation trace in in-memory cache."""
    key = get_cache_key(
        query_dict.get("title", ""),
        query_dict.get("artist", ""),
        query_dict.get("duration_ms", 0),
        query_dict.get("album"),
    )
    MATCH_TRACE_CACHE[key] = trace


def get_cached_match_trace(
    title: str, artist: str, duration_ms: int = 0, album: str | None = None
) -> dict | None:
    """Retrieve cached match trace if available."""
    key = get_cache_key(title, artist, duration_ms, album)
    if key in MATCH_TRACE_CACHE:
        return MATCH_TRACE_CACHE[key]

    # Flexible fallback: match title + artist with duration tolerance ±5000ms
    t_clean = key[0]
    a_clean = key[1]
    dur = key[2]
    for (ct, ca, cd), trace in MATCH_TRACE_CACHE.items():
        if ct == t_clean and ca == a_clean:
            if dur == 0 or cd == 0 or abs(dur - cd) <= 5000:
                return trace
    return None


def clear_match_trace_cache() -> None:
    """Clear all cached match traces."""
    MATCH_TRACE_CACHE.clear()


def select_highest_quality_media(media_files: list[Any]) -> Any | None:
    """
    Select the edition with the highest bitrate/sample rate as the primary playback reference.

    Preference hierarchy:
    1. Lossless format (flac, wav, alac, aiff, dsd)
    2. Bitrate (bps / kbps)
    3. Sample rate (Hz)
    4. Bit depth (bits)
    """
    if not media_files:
        return None

    def _sort_key(m: Any) -> tuple[int, int, int, int]:
        fmt = getattr(m, "file_format", None) or (
            m.get("file_format") if isinstance(m, dict) else ""
        )
        fmt = str(fmt or "").lower().strip()
        is_lossless = 1 if fmt in LOSSLESS_FORMATS else 0

        bitrate = getattr(m, "bitrate", None) or (
            m.get("bitrate") if isinstance(m, dict) else 0
        )
        sample_rate = getattr(m, "sample_rate", None) or (
            m.get("sample_rate") if isinstance(m, dict) else 0
        )
        bit_depth = getattr(m, "bit_depth", None) or (
            m.get("bit_depth") if isinstance(m, dict) else 0
        )

        return (
            is_lossless,
            int(bitrate or 0),
            int(sample_rate or 0),
            int(bit_depth or 0),
        )

    return max(media_files, key=_sort_key)


def _strip_feat(title: str) -> str:
    """Strip featured artist annotations from title."""
    if not title:
        return ""
    cleaned = re.sub(
        r"\s*[\(\[\{]\s*(feat\.?|featuring|with)\b[^\)\]\}]*[\)\]\}]",
        "",
        title,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\s+(feat\.?|featuring|with)\b.*$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned.strip() or title


def _fetch_candidates_tier1(conn, search_title: str, base_search_title: str, track_artist: str, track_duration: int):
    """Retrieve Tier 1 candidates using SQL connection."""
    expanded_terms = hook_manager.apply_filters(
        "search_expansion",
        [],
        title=search_title,
        artist=track_artist,
    )
    if not isinstance(expanded_terms, list):
        expanded_terms = []

    seen_terms = {search_title.lower(), base_search_title.lower()}
    clean_expanded = []
    for t in expanded_terms:
        if isinstance(t, str) and t.strip() and t.strip().lower() not in seen_terms:
            seen_terms.add(t.strip().lower())
            clean_expanded.append(t.strip())

    title_norm = search_title.replace("\u2019", "'").replace("\u2018", "'")
    norm_search = _normalize_candidate_title(search_title) or search_title

    params: dict[str, Any] = {
        "artist_exact": track_artist,
        "artist_pattern": f"%{track_artist}%",
        "title_exact": search_title,
        "title_pattern": f"%{search_title}%",
        "base_title_pattern": f"%{base_search_title}%",
        "title_norm_pattern": f"%{title_norm}%",
        "norm_search_pattern": f"%{norm_search}%",
        "duration": track_duration or 0,
    }

    def _am(param: str) -> str:
        return (
            f"(LOWER(t.title) LIKE LOWER(:{param})"
            f" OR (t.sort_title IS NOT NULL AND LOWER(t.sort_title) LIKE LOWER(:{param}))"
            f" OR (t.normalized_title IS NOT NULL AND LOWER(t.normalized_title) LIKE LOWER(:{param}))"
            f" OR EXISTS (SELECT 1 FROM track_aliases ta_x"
            f" WHERE ta_x.track_id = t.id AND LOWER(ta_x.name) LIKE LOWER(:{param})))"
        )

    base_where = (
        f"{_am('title_pattern')}\n"
        f"        OR {_am('base_title_pattern')}\n"
        f"        OR {_am('norm_search_pattern')}\n"
        f"        OR (LOWER(REPLACE(REPLACE(t.title, char(8217), char(39)), char(8216), char(39)))"
        f" LIKE LOWER(:title_norm_pattern))"
    )

    exp_parts = []
    for i, term in enumerate(clean_expanded):
        pkey = f"exp_{i}"
        params[pkey] = f"%{term}%"
        exp_parts.append(_am(pkey))
    exp_where = ("\n        OR " + "\n        OR ".join(exp_parts)) if exp_parts else ""

    from core.matching_engine.text_utils import split_artist_collaborators

    primary_art, collabs = split_artist_collaborators(track_artist or "")
    all_artists = ([primary_art] + collabs) if primary_art else ([track_artist] if track_artist else [])

    artist_order_parts = [
        "(LOWER(a.name) = LOWER(:artist_exact) OR (a.sort_name IS NOT NULL AND LOWER(a.sort_name) = LOWER(:artist_exact)) OR (ta_a.name IS NOT NULL AND LOWER(ta_a.name) = LOWER(:artist_exact)) OR (alb_a.name IS NOT NULL AND LOWER(alb_a.name) = LOWER(:artist_exact)))"
    ]
    for i, art in enumerate(all_artists):
        k = f"art_token_{i}"
        params[k] = art
        artist_order_parts.append(
            f"(LOWER(a.name) = LOWER(:{k}) OR (a.sort_name IS NOT NULL AND LOWER(a.sort_name) = LOWER(:{k})) OR (ta_a.name IS NOT NULL AND LOWER(ta_a.name) = LOWER(:{k})) OR (alb_a.name IS NOT NULL AND LOWER(alb_a.name) = LOWER(:{k})))"
        )
    artist_order_sql = " OR ".join(artist_order_parts)

    sql = text(f"""
        SELECT DISTINCT t.id, t.title, t.duration, t.edition,
               a.name AS artist_name, a.id AS artist_id,
               t.sort_title, al.title AS album_title, lm.file_path, t.sync_id
        FROM tracks t
        JOIN artists a ON t.artist_id = a.id
        LEFT JOIN track_artists ta ON t.id = ta.track_id
        LEFT JOIN artists ta_a ON ta.artist_id = ta_a.id
        LEFT JOIN albums al ON t.album_id = al.id
        LEFT JOIN artists alb_a ON al.artist_id = alb_a.id
        JOIN local_media lm ON t.id = lm.track_id
        WHERE ({base_where}{exp_where})
        ORDER BY
            ({artist_order_sql}) DESC,
            (LOWER(t.title) = LOWER(:title_exact)) DESC,
            ABS(t.duration - :duration) ASC
        LIMIT 50
    """)

    return conn.execute(sql, params).fetchall()


def _fetch_candidates_tier2(conn, search_title: str, track_duration: int, duration_window_ms: int = 10000):
    """Retrieve Tier 2 candidates using SQL connection."""
    expanded_terms = hook_manager.apply_filters(
        "search_expansion",
        [],
        title=search_title,
        artist="",
    )
    if not isinstance(expanded_terms, list):
        expanded_terms = []

    seen_terms = {search_title.lower()}
    clean_expanded = []
    for t in expanded_terms:
        if isinstance(t, str) and t.strip() and t.strip().lower() not in seen_terms:
            seen_terms.add(t.strip().lower())
            clean_expanded.append(t.strip())

    norm_search = _normalize_candidate_title(search_title) or search_title
    params: dict[str, Any] = {
        "title_exact": search_title,
        "title_pattern": f"%{search_title}%",
        "norm_search_pattern": f"%{norm_search}%",
        "duration": track_duration,
    }

    base_where = (
        "LOWER(t.title) LIKE LOWER(:title_pattern)\n"
        "        OR (t.sort_title IS NOT NULL AND LOWER(t.sort_title) LIKE LOWER(:title_pattern))\n"
        "        OR (t.normalized_title IS NOT NULL AND LOWER(t.normalized_title) LIKE LOWER(:norm_search_pattern))\n"
        "        OR EXISTS (SELECT 1 FROM track_aliases ta_x\n"
        "                   WHERE ta_x.track_id = t.id AND (LOWER(ta_x.name) LIKE LOWER(:title_pattern) OR LOWER(ta_x.name) LIKE LOWER(:norm_search_pattern)))"
    )

    exp_parts = []
    for i, term in enumerate(clean_expanded):
        pkey = f"exp_{i}"
        params[pkey] = f"%{term}%"
        exp_parts.append(
            f"(LOWER(t.title) LIKE LOWER(:{pkey})"
            f" OR (t.sort_title IS NOT NULL AND LOWER(t.sort_title) LIKE LOWER(:{pkey}))"
            f" OR (t.normalized_title IS NOT NULL AND LOWER(t.normalized_title) LIKE LOWER(:{pkey}))"
            f" OR EXISTS (SELECT 1 FROM track_aliases ta_x"
            f" WHERE ta_x.track_id = t.id AND LOWER(ta_x.name) LIKE LOWER(:{pkey})))"
        )
    exp_where = ("\n        OR " + "\n        OR ".join(exp_parts)) if exp_parts else ""

    sql = text(f"""
        SELECT DISTINCT t.id, t.title, t.duration, t.edition,
               a.name AS artist_name, a.id AS artist_id,
               t.sort_title, al.title AS album_title, lm.file_path, t.sync_id
        FROM tracks t
        JOIN artists a ON t.artist_id = a.id
        LEFT JOIN albums al ON t.album_id = al.id
        JOIN local_media lm ON t.id = lm.track_id
        WHERE ({base_where}{exp_where})
        ORDER BY
            (LOWER(t.title) = LOWER(:title_exact)) DESC,
            ABS(t.duration - :duration) ASC
        LIMIT 50
    """)

    return conn.execute(sql, params).fetchall()


def evaluate_single_track_diagnostics(
    title: str,
    artist: str,
    duration_ms: int = 0,
    album: str | None = None,
    db: Any | None = None,
    matching_engine: WeightedMatchingEngine | None = None,
) -> dict:
    """
    Run the canonical matching pipeline for a single track and return structured match trace.
    Provides 100% parity with batch playlist sync evaluation.
    """
    if db is None:
        db = db_mod.MusicDatabase()
    profile = ExactSyncProfile()
    if matching_engine is None:
        matching_engine = WeightedMatchingEngine(profile)

    clean_search_title = _strip_feat(title or "")
    base_search_title = re.sub(r"\s*[\(\[].*?[\)\]]", "", clean_search_title).strip()
    base_search_title = re.sub(r"\s+-.*$", "", base_search_title).strip() or clean_search_title

    source_track = EchosyncTrack(
        raw_title=title,
        artist_name=artist,
        album_title=album or "",
        duration=duration_ms,
    )
    hook_manager.apply_filters(
        "pre_normalize_title",
        source_track.raw_title,
        plugin_context=source_track.plugin_context,
    )
    clean_src = _normalize_candidate_title(
        source_track.raw_title,
        plugin_context=source_track.plugin_context,
    )
    if clean_src:
        source_track.title = clean_src

    candidate_rows = []
    seen_ids = set()

    with db.engine.connect() as conn:
        t1_rows = _fetch_candidates_tier1(conn, clean_search_title, base_search_title, artist, duration_ms)
        for r in t1_rows:
            if r[0] not in seen_ids:
                seen_ids.add(r[0])
                candidate_rows.append(r)

        if duration_ms and len(candidate_rows) < 10:
            t2_rows = _fetch_candidates_tier2(conn, clean_search_title, duration_ms, 10000)
            for r in t2_rows:
                if r[0] not in seen_ids:
                    seen_ids.add(r[0])
                    candidate_rows.append(r)

    # If no SQL rows found, query candidate tracks via ORM session fallback
    if not candidate_rows:
        with db.session_scope() as session:
            from services.playlists_api import get_library_candidates
            orm_candidates = get_library_candidates(session, clean_search_title, artist)
            for cand in orm_candidates:
                if cand.id not in seen_ids:
                    seen_ids.add(cand.id)
                    highest_media = select_highest_quality_media(cand.media_files)
                    media_path = highest_media.file_path if highest_media else None
                    candidate_rows.append((
                        cand.id,
                        cand.title,
                        cand.duration,
                        cand.edition,
                        cand.artist.name if cand.artist else "",
                        cand.artist_id,
                        cand.sort_title,
                        cand.album.title if cand.album else "",
                        media_path,
                        cand.sync_id or str(cand.id),
                    ))

    candidate_evaluations: list[dict] = []
    best_candidate_eval = None
    best_score = 0.0

    # Fetch track and artist aliases
    alias_map: dict[int, list[str]] = {}
    artist_alias_map: dict[int, list[str]] = {}
    if candidate_rows:
        try:
            cids = [int(r[0]) for r in candidate_rows]
            with db.engine.connect() as ac:
                for ar in ac.execute(
                    text("SELECT track_id, name FROM track_aliases WHERE track_id IN (" + ",".join(str(c) for c in cids) + ")")
                ).fetchall():
                    alias_map.setdefault(ar[0], []).append(ar[1])
                
                a_ids = list({int(r[5]) for r in candidate_rows if r[5] is not None})
                if a_ids:
                    for aar in ac.execute(
                        text("SELECT artist_id, name FROM artist_aliases WHERE artist_id IN (" + ",".join(str(a) for a in a_ids) + ")")
                    ).fetchall():
                        artist_alias_map.setdefault(aar[0], []).append(aar[1])
        except Exception as ex:
            logger.debug(f"Alias query error: {ex}")

    for row in candidate_rows:
        cand_id = row[0]
        raw_t = row[1]
        cand_dur = parse_duration_to_ms(row[2]) if row[2] else 0
        cand_ed = row[3]
        cand_artist = row[4] or ""
        cand_artist_id = row[5]
        cand_sort_t = row[6] if len(row) > 6 else None
        cand_album = row[7] if len(row) > 7 else ""
        media_path = row[8] if len(row) > 8 else None
        sync_id = row[9] if len(row) > 9 and row[9] else str(cand_id)

        cand_track = EchosyncTrack(
            raw_title=raw_t,
            artist_name=cand_artist,
            album_title=cand_album or "",
            duration=cand_dur,
            edition=cand_ed,
            sync_id=sync_id,
        )
        hook_manager.apply_filters(
            "pre_normalize_title",
            cand_track.raw_title,
            plugin_context=cand_track.plugin_context,
        )

        clean_cand_t = _normalize_candidate_title(
            raw_t,
            plugin_context=cand_track.plugin_context,
        )
        best_cand_t = clean_cand_t or cand_track.title
        for al in alias_map.get(cand_id, []):
            if al and _cmp_titles(source_track.title, al) > _cmp_titles(source_track.title, best_cand_t):
                best_cand_t = al
        if best_cand_t:
            cand_track.title = best_cand_t

        best_art = cand_track.artist_name or ""
        for art_al in artist_alias_map.get(cand_artist_id, []):
            if art_al and _cmp_artists(source_track.artist_name, art_al) > _cmp_artists(source_track.artist_name, best_art):
                best_art = art_al
        if best_art:
            cand_track.artist_name = best_art

        match_res = matching_engine.calculate_match(source_track, cand_track)
        confidence = min(100.0, max(0.0, match_res.confidence_score))

        delta_sec = round(abs(cand_dur - duration_ms) / 1000.0, 2) if (cand_dur and duration_ms) else 0.0
        accepted = confidence >= profile.weights.min_confidence_to_accept

        rejection_reason = None
        if not accepted:
            if not match_res.passed_version_check:
                rejection_reason = f"Version mismatch: {match_res.reasoning}"
            elif delta_sec > 6.0 and match_res.duration_match_score == 0.0:
                rejection_reason = f"Duration Delta > 6.0s ({delta_sec}s)"
            else:
                rejection_reason = f"Confidence {confidence:.1f}% below threshold {profile.weights.min_confidence_to_accept:.1f}%"

        penalties = match_res.penalties or {}
        if match_res.version_penalty_applied > 0:
            penalties["version_penalty"] = match_res.version_penalty_applied
        if match_res.edition_penalty_applied > 0:
            penalties["edition_penalty"] = match_res.edition_penalty_applied

        eval_item = {
            "track_sync_id": sync_id,
            "track_id": cand_id,
            "title": raw_t or cand_track.title,
            "artist": cand_artist or cand_track.artist_name,
            "album": cand_album,
            "duration_ms": cand_dur,
            "duration_delta_sec": delta_sec,
            "title_score": round(match_res.title_score, 2),
            "artist_score": round(match_res.artist_score, 2),
            "duration_score": round(match_res.duration_match_score, 2),
            "album_score": round(match_res.album_score, 2),
            "penalties": penalties,
            "composite_score": round(confidence, 2),
            "accepted": accepted,
            "rejection_reason": rejection_reason,
        }
        candidate_evaluations.append(eval_item)

        if confidence > best_score:
            best_score = confidence
            best_candidate_eval = eval_item

    candidate_evaluations.sort(key=lambda c: c["composite_score"], reverse=True)
    best_match = best_candidate_eval if (best_candidate_eval and best_candidate_eval["accepted"]) else (candidate_evaluations[0] if candidate_evaluations and candidate_evaluations[0]["accepted"] else None)

    trace = {
        "query": {
            "title": title,
            "artist": artist,
            "duration_ms": duration_ms,
            "album": album,
        },
        "candidates_located_count": len(candidate_evaluations),
        "candidates_retrieved_count": len(candidate_evaluations),
        "evaluated_candidates": candidate_evaluations,
        "candidates": candidate_evaluations,
        "best_match": best_match,
        "winning_threshold": profile.weights.min_confidence_to_accept,
    }

    cache_match_trace(trace["query"], trace)
    return trace


def analyze_playlist(
    source_provider: Any = None,
    playlist_id: str | None = None,
    playlist_name: str = "Unknown Playlist",
    tracks: list[Any] | None = None,
    target_source: str | None = None,
    target_quality: str | None = None,
    db: Any | None = None,
    matching_engine: WeightedMatchingEngine | None = None,
) -> dict[str, Any]:
    """
    Analyze a playlist's tracks against the local library without gating candidates by target_quality.
    
    Selects the highest quality available media file for each candidate, but marks tracks as 'Found'
    regardless of whether they meet target_quality. Restricts target_quality exclusively for download queue.
    """
    if db is None:
        db = db_mod.MusicDatabase()
    profile = ExactSyncProfile()
    if matching_engine is None:
        matching_engine = WeightedMatchingEngine(profile)

    source_tracks = []
    if tracks:
        source_tracks = tracks
    elif source_provider and playlist_id:
        import inspect
        sig = inspect.signature(source_provider.get_playlist_tracks)
        if "force_refresh" in sig.parameters:
            source_tracks = source_provider.get_playlist_tracks(playlist_id, force_refresh=True)
        else:
            source_tracks = source_provider.get_playlist_tracks(playlist_id)

    all_tracks = []
    found_count = 0
    missing_count = 0

    for item in source_tracks:
        if isinstance(item, dict):
            track_title = item.get("title") or item.get("raw_title") or ""
            track_artist = item.get("artist") or item.get("artist_name") or ""
            track_album = item.get("album") or item.get("album_title") or ""
            track_duration = item.get("duration_ms") or item.get("duration") or 0
            if isinstance(track_duration, str):
                track_duration = parse_duration_to_ms(track_duration)
            item_id = item.get("id") or item.get("playlist_track_id")
            item_isrc = item.get("isrc")
            source_track_dict = item
        else:
            track_title = getattr(item, "title", "")
            track_artist = getattr(item, "artist_name", "") or getattr(item, "artist", "")
            track_album = getattr(item, "album_title", "") or getattr(item, "album", "")
            track_duration = getattr(item, "duration", 0) or getattr(item, "duration_ms", 0)
            item_id = getattr(item, "id", None)
            item_isrc = getattr(item, "isrc", None)
            source_track_dict = item.to_dict() if hasattr(item, "to_dict") else None

        # Execute single track diagnostics matching pipeline
        trace = evaluate_single_track_diagnostics(
            title=track_title,
            artist=track_artist,
            duration_ms=track_duration,
            album=track_album,
            db=db,
            matching_engine=matching_engine,
        )

        candidates = trace.get("candidates", [])
        best_match = trace.get("best_match")
        best_score = best_match.get("composite_score", 0.0) if best_match else (candidates[0]["composite_score"] if candidates else 0.0)
        matched_track_id = best_match.get("track_id") if best_match else None

        if matched_track_id is None and candidates and candidates[0]["accepted"]:
            best_match = candidates[0]
            matched_track_id = best_match["track_id"]
            best_score = best_match["composite_score"]

        # Selection of highest quality media file for the matched track
        primary_media_path = None
        if matched_track_id is not None:
            try:
                with db.session_scope() as session:
                    t_rec = session.query(Track).filter_by(id=matched_track_id).options(joinedload(Track.media_files)).first()
                    if t_rec and t_rec.media_files:
                        highest_media = select_highest_quality_media(t_rec.media_files)
                        if highest_media:
                            primary_media_path = highest_media.file_path
            except Exception as e:
                logger.debug(f"Media file lookup error for track {matched_track_id}: {e}")

        matched = bool(matched_track_id and best_score >= 70.0)
        if matched:
            if best_score >= 85:
                library_match = "Found"
            else:
                library_match = f"Found (score: {int(best_score)}%)"
            found_count += 1
            status = "found"
        else:
            library_match = "Not Found"
            missing_count += 1
            status = "not_found"

        duration_str = "–"
        if track_duration:
            mins = track_duration // 60000
            secs = (track_duration % 60000) // 1000
            duration_str = f"{mins}:{secs:02d}"

        valid_candidates = [
            {"id": c["track_id"], "score": c["composite_score"], "title": c["title"], "artist": c["artist"]}
            for c in candidates if c["composite_score"] >= 70
        ]

        track_summary = {
            "playlist": playlist_name,
            "playlist_track_id": item_id,
            "title": track_title,
            "artist": track_artist,
            "album": track_album,
            "duration": duration_str,
            "duration_ms": track_duration,
            "isrc": item_isrc,
            "status": status,
            "library_match": library_match,
            "download_status": "-",
            "matched_track_id": matched_track_id if matched else None,
            "primary_media_path": primary_media_path,
            "match_score": best_score,
            "rejection_reason": candidates[0].get("rejection_reason") if (candidates and not matched) else None,
            "candidate_matches": valid_candidates,
            "target_source": target_source,
            "target_identifier": None,
            "target_exists": False,
            "source_track": source_track_dict,
            "match_diagnostics": trace,
        }
        all_tracks.append(track_summary)

    all_tracks = resolve_duplicate_matches(all_tracks)
    total_tracks = len(all_tracks)
    found_count = sum(1 for t in all_tracks if t.get("matched_track_id"))
    missing_count = total_tracks - found_count

    matched_pairs = []
    missing_tracks = []
    for t in all_tracks:
        if t.get("matched_track_id"):
            matched_pairs.append({
                "track_id": t["matched_track_id"],
                "matched_track_id": t["matched_track_id"],
                "title": t.get("title"),
                "artist": t.get("artist"),
                "album": t.get("album"),
                "duration_ms": t.get("duration_ms"),
                "source_title": t.get("title"),
                "source_artist": t.get("artist"),
                "source_track": t.get("source_track"),
                "primary_media_path": t.get("primary_media_path"),
            })
        else:
            missing_tracks.append({
                "title": t["title"],
                "artist": t["artist"],
                "album": t["album"],
                "duration": t.get("duration_ms"),
                "duration_ms": t.get("duration_ms"),
                "isrc": t.get("isrc"),
                "source_track": t.get("source_track"),
                "rejection_reason": t.get("rejection_reason"),
            })

    return {
        "summary": {
            "total_tracks": total_tracks,
            "found_in_library": found_count,
            "missing_tracks": missing_count,
            "downloaded": 0,
            "quality_profile": target_quality or "Auto",
            "target_quality": target_quality or "Auto",
            "source": getattr(source_provider, "name", "unknown") if source_provider else "unknown",
            "target": target_source,
            "matched_pairs": matched_pairs,
            "can_sync": len(matched_pairs) > 0,
        },
        "tracks": all_tracks,
        "missing": missing_tracks,
    }


def analyze_playlists(
    source: Any,
    target_source: str | None,
    playlists: list[dict] | dict,
    target_quality: str | None = "Auto",
    db: Any | None = None,
) -> dict[str, Any]:
    """Analyze multiple playlists or a single playlist dict."""
    if isinstance(playlists, dict):
        playlists = [playlists]

    if db is None:
        db = db_mod.MusicDatabase()

    matching_engine = WeightedMatchingEngine(ExactSyncProfile())

    from web.routes.playlists import _get_provider_for_account, _normalize_provider_short_name

    target_source_canonical = (
        _normalize_provider_short_name(target_source) if target_source else target_source
    )

    needs_provider = any(not p.get("tracks") for p in playlists if isinstance(p, dict))
    source_provider = None
    caps = None
    if isinstance(source, str) and needs_provider:
        source_provider, _ = _get_provider_for_account(source, None)
        if source_provider:
            caps = getattr(source_provider, "capabilities", None)
    elif not isinstance(source, str):
        source_provider = source
        caps = getattr(source_provider, "capabilities", None)

    all_tracks = []
    found_count = 0
    missing_count = 0

    for playlist_info in playlists:
        playlist_id = playlist_info.get("id")
        playlist_name = playlist_info.get("name", "Unknown Playlist")
        provided_tracks = playlist_info.get("tracks")

        provider_to_use = source_provider
        acc_id = playlist_info.get("account_id")
        if acc_id and caps and getattr(caps, "supports_user_auth", False):
            inst, _ = _get_provider_for_account(source, acc_id)
            if inst:
                provider_to_use = inst

        res = analyze_playlist(
            source_provider=provider_to_use,
            playlist_id=playlist_id,
            playlist_name=playlist_name,
            tracks=provided_tracks,
            target_source=target_source_canonical,
            target_quality=target_quality,
            db=db,
            matching_engine=matching_engine,
        )
        all_tracks.extend(res.get("tracks", []))

    all_tracks = resolve_duplicate_matches(all_tracks)
    total_tracks = len(all_tracks)
    found_count = sum(1 for t in all_tracks if t.get("matched_track_id"))
    missing_count = total_tracks - found_count

    matched_pairs = []
    missing_tracks = []
    for track in all_tracks:
        if track.get("matched_track_id"):
            matched_pairs.append({
                "track_id": track["matched_track_id"],
                "matched_track_id": track["matched_track_id"],
                "target_identifier": track.get("target_identifier"),
                "title": track.get("title"),
                "artist": track.get("artist"),
                "album": track.get("album"),
                "duration_ms": track.get("duration_ms"),
                "source_title": track.get("title"),
                "source_artist": track.get("artist"),
                "source_track": track.get("source_track"),
                "primary_media_path": track.get("primary_media_path"),
            })
        else:
            missing_tracks.append({
                "title": track["title"],
                "artist": track["artist"],
                "album": track["album"],
                "duration": track.get("duration_ms"),
                "duration_ms": track.get("duration_ms"),
                "isrc": track.get("isrc"),
                "source_track": track.get("source_track"),
                "rejection_reason": track.get("rejection_reason"),
            })

    return {
        "summary": {
            "total_tracks": total_tracks,
            "found_in_library": found_count,
            "missing_tracks": missing_count,
            "downloaded": 0,
            "quality_profile": target_quality,
            "target_quality": target_quality,
            "source": source if isinstance(source, str) else getattr(source, "name", "unknown"),
            "target": target_source_canonical or target_source,
            "matched_pairs": matched_pairs,
            "can_sync": len(matched_pairs) > 0,
        },
        "tracks": all_tracks,
        "missing": missing_tracks,
    }


class PlaylistSyncService:
    """Wrapper class providing object-oriented interface for playlist sync service."""

    def __init__(self, db: Any | None = None):
        self.db = db or db_mod.MusicDatabase()
        self.matching_engine = WeightedMatchingEngine(ExactSyncProfile())

    def analyze_playlist(self, *args, **kwargs):
        if "db" not in kwargs:
            kwargs["db"] = self.db
        if "matching_engine" not in kwargs:
            kwargs["matching_engine"] = self.matching_engine
        return analyze_playlist(*args, **kwargs)

    def analyze_playlists(self, *args, **kwargs):
        if "db" not in kwargs:
            kwargs["db"] = self.db
        return analyze_playlists(*args, **kwargs)

    def select_highest_quality_media(self, media_files: list[Any]) -> Any | None:
        return select_highest_quality_media(media_files)
