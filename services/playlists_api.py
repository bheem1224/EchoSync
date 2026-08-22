#!/usr/bin/env python3
"""
Playlists API and Library Candidate Query Service
Provides multi-candidate retrieval supporting Various Artists compilations,
track artist / album artist fallback, and title variant matching.
"""

from typing import List, Optional
import re
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from database.music_database import Track, Artist, Album, LocalMedia, TrackArtist
from core.matching_engine.text_utils import (
    normalize_text,
    normalize_title,
    normalize_track_comparison_fields,
    split_artist_collaborators,
    _OST_SAFE_RE,
    _cmp_titles,
)
from core.tiered_logger import get_logger

logger = get_logger("playlists_api")

REMASTER_STRIP_REGEX = re.compile(
    r"\s*[-–—\(\[]\s*(?:\d{4}\s+)?remaster(?:ed)?(?:\s+\d{4})?\s*[\)\]]?",
    re.IGNORECASE
)


def normalize_title_for_search(title: str) -> str:
    """Normalize title for SQL search, stripping remaster noise and parentheticals."""
    if not title:
        return ""
    clean = REMASTER_STRIP_REGEX.sub("", title).strip()
    return normalize_title(clean) or clean.lower()


def normalize_artist_for_search(artist: str) -> str:
    """Normalize artist for SQL search."""
    if not artist:
        return ""
    return normalize_text(artist) or artist.lower()


def sanitize_title_for_comparison(title: str) -> str:
    """Strip remaster, remix, and version suffixes from title before comparison."""
    if not title:
        return ""
    return normalize_title(title) or REMASTER_STRIP_REGEX.sub("", title).strip()


def check_cover_rejection(source_title: str, source_artist: str, candidate_diagnostics: List[dict]) -> bool:
    """
    Determine if Tier 1 candidate evaluation rejected candidates solely due to
    disjoint artist cover mismatch on high-similarity titles.
    
    If True, Tier 2 (title-only) escalation must be aborted to prevent covers
    by distinct artists from falsely claiming physical library files.
    """
    if not source_title or not source_artist:
        return False
        
    src_norm = normalize_title(source_title)
    from core.matching_engine.text_utils import _cmp_artists, is_franchise_entity
    from difflib import SequenceMatcher

    if is_franchise_entity(source_artist):
        return False
    
    for cand_diag in candidate_diagnostics:
        cand = cand_diag.get("candidate", {})
        cand_title = cand.get("title", "")
        cand_artist = cand.get("artist", "")

        if is_franchise_entity(cand_artist):
            continue
        
        cand_norm = normalize_title(cand_title)
        t_sim = SequenceMatcher(None, src_norm, cand_norm).ratio() if (src_norm and cand_norm) else 0.0
        if t_sim < 0.90:
            t_sim = _cmp_titles(source_title, cand_title)
            
        if t_sim >= 0.90:
            art_sim = _cmp_artists(source_artist, cand_artist)
            reasoning = cand_diag.get("reasoning", "")
            if art_sim < 0.60 or "Artist boundary mismatch" in reasoning:
                return True
                
    return False


def get_library_candidates(session: Session, target_title: str, target_artist: str) -> List[Track]:
    """
    Fetch all matching candidate Track records for a given title and artist.
    
    Supports:
    1. Multi-Token Artist Matching: Decomposes collaborative strings (e.g. 'W&W & AXMO',
       'Jonas Blue feat. William Singe') via split_artist_collaborators so any credited
       artist token matches Track.artist, Artist.name, Artist.sort_name, Album.artist,
       or collaborating artists in track_artists.
    2. Multi-Candidate Retention: Returns all matching local media records for the
       (artist, title) tuple so downstream matching engines can evaluate durations
       for both original cuts and remixes simultaneously.
    3. Eager Loading: Fully eager-loads Track.media_files, Track.artist, and Track.album.
    
    Args:
        session: SQLAlchemy Session
        target_title: Target track title
        target_artist: Target track artist
        
    Returns:
        List of candidate Track records with loaded media_files, artist, and album.
    """
    clean_title = normalize_title_for_search(target_title)
    raw_title_clean = (target_title or "").strip()

    title_filter = or_(
        Track.normalized_title == clean_title,
        Track.title.ilike(f"%{clean_title}%"),
        Track.title.ilike(f"%{raw_title_clean}%"),
    )
    if Track.sort_title is not None:
        title_filter = or_(
            title_filter,
            Track.sort_title.ilike(f"%{clean_title}%"),
            Track.sort_title.ilike(f"%{raw_title_clean}%"),
        )

    # Multi-Token Artist Expansion
    primary_art, collabs = split_artist_collaborators(target_artist or "")
    all_artists = ([primary_art] + collabs) if primary_art else ([target_artist] if target_artist else [])
    
    artist_clauses = []
    # Always include full un-split string
    clean_full_artist = normalize_artist_for_search(target_artist)
    raw_full_artist = (target_artist or "").strip()
    if clean_full_artist:
        artist_clauses.extend([
            Artist.normalized_name == clean_full_artist,
            Artist.name.ilike(f"%{clean_full_artist}%"),
            Artist.name.ilike(f"%{raw_full_artist}%"),
            Artist.sort_name.ilike(f"%{clean_full_artist}%"),
            Artist.sort_name.ilike(f"%{raw_full_artist}%"),
        ])

    for art in all_artists:
        clean_art = normalize_artist_for_search(art)
        raw_art = (art or "").strip()
        if clean_art:
            artist_clauses.extend([
                Artist.normalized_name == clean_art,
                Artist.name.ilike(f"%{clean_art}%"),
                Artist.name.ilike(f"%{raw_art}%"),
                Artist.sort_name.ilike(f"%{clean_art}%"),
                Artist.sort_name.ilike(f"%{raw_art}%"),
            ])

    query = (
        session.query(Track)
        .outerjoin(TrackArtist, Track.id == TrackArtist.track_id)
        .outerjoin(Artist, or_(Track.artist_id == Artist.id, TrackArtist.artist_id == Artist.id))
        .outerjoin(Album, Track.album_id == Album.id)
        .outerjoin(LocalMedia, Track.id == LocalMedia.track_id)
        .options(
            joinedload(Track.media_files),
            joinedload(Track.artist),
            joinedload(Track.album),
            joinedload(Track.artist_associations).joinedload(TrackArtist.artist),
        )
        .filter(title_filter, or_(*artist_clauses) if artist_clauses else True)
        .distinct()
    )

    candidates = query.all()
    if not candidates and clean_title:
        # Fallback: broad search by title only if artist was 'Various Artists' or missing
        fallback_query = (
            session.query(Track)
            .outerjoin(TrackArtist, Track.id == TrackArtist.track_id)
            .outerjoin(Artist, or_(Track.artist_id == Artist.id, TrackArtist.artist_id == Artist.id))
            .outerjoin(Album, Track.album_id == Album.id)
            .outerjoin(LocalMedia, Track.id == LocalMedia.track_id)
            .options(
                joinedload(Track.media_files),
                joinedload(Track.artist),
                joinedload(Track.album),
                joinedload(Track.artist_associations).joinedload(TrackArtist.artist),
            )
            .filter(title_filter)
            .distinct()
            .limit(50)
        )
        candidates = fallback_query.all()

    return candidates


# Aliases for Tier 1 candidate querying
query_tier1_candidates = get_library_candidates
_fetch_tier1_candidates = get_library_candidates


def resolve_duplicate_matches(all_tracks: List[dict]) -> List[dict]:
    """
    Greedy 1:1 Winner-Take-All Candidate Assignment.
    
    When multiple playlist source tracks match the same local track ID (e.g., covers or duplicate titles),
    allocates the local track strictly to the source track with the highest match score.
    
    Losers evaluate remaining fallback candidates in their candidate pool (score >= 70)
    or are marked as unmatched with explicit collision rejection reasoning.
    """
    claimed: dict[int, dict] = {}
    
    # Sort descending by match score to grant priority to best match
    sorted_tracks = sorted(
        [t for t in all_tracks if t.get("matched_track_id")],
        key=lambda x: x.get("match_score", 0.0),
        reverse=True
    )
    
    for track in sorted_tracks:
        tid = track["matched_track_id"]
        if tid not in claimed:
            claimed[tid] = track
        else:
            # Demote loser to fallback or unmatched
            fallback_found = False
            for fallback in track.get("candidate_matches", []):
                f_id = fallback.get("id")
                if f_id and f_id not in claimed and fallback.get("score", 0) >= 70:
                    track["matched_track_id"] = f_id
                    track["match_score"] = fallback["score"]
                    track["target_identifier"] = fallback.get("target_identifier")
                    track["target_exists"] = bool(fallback.get("target_identifier"))
                    track["library_match"] = "Found" if fallback["score"] >= 85 else f"Found (score: {int(fallback['score'])}%)"
                    claimed[f_id] = track
                    fallback_found = True
                    break
            
            if not fallback_found:
                winner_artist = claimed[tid].get("artist", "Unknown")
                track["matched_track_id"] = None
                track["library_match"] = "Not Found"
                track["target_identifier"] = None
                track["target_exists"] = False
                track["rejection_reason"] = f"Collision: local track assigned to higher confidence match ({winner_artist})"

    return all_tracks


_resolve_duplicate_matches = resolve_duplicate_matches
