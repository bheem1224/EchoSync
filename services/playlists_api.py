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

from database.music_database import Track, Artist, Album, LocalMedia
from core.matching_engine.text_utils import (
    normalize_text,
    normalize_title,
    normalize_track_comparison_fields,
    split_artist_collaborators,
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
    """Normalize artist for SQL search, stripping featured collaborators."""
    if not artist:
        return ""
    _, clean = normalize_track_comparison_fields("", artist)
    return normalize_text(clean) or clean.lower()


def sanitize_title_for_comparison(title: str) -> str:
    """Strip remaster suffixes from title before comparison."""
    if not title:
        return ""
    return REMASTER_STRIP_REGEX.sub("", title).strip()


def get_library_candidates(session: Session, target_title: str, target_artist: str) -> List[Track]:
    """
    Fetch all matching candidate Track records for a given title and artist.
    
    Supports:
    1. Multi-Token Artist Matching: Decomposes collaborative strings (e.g. 'W&W & AXMO',
       'Jonas Blue feat. William Singe') via split_artist_collaborators so any credited
       artist token matches Track.artist, Artist.name, Artist.sort_name, or Album.artist.
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
        .join(Artist, Track.artist_id == Artist.id)
        .outerjoin(Album, Track.album_id == Album.id)
        .outerjoin(LocalMedia, Track.id == LocalMedia.track_id)
        .options(
            joinedload(Track.media_files),
            joinedload(Track.artist),
            joinedload(Track.album),
        )
        .filter(title_filter, or_(*artist_clauses) if artist_clauses else True)
        .distinct()
    )

    candidates = query.all()
    if not candidates and clean_title:
        # Fallback: broad search by title only if artist was 'Various Artists' or missing
        fallback_query = (
            session.query(Track)
            .join(Artist, Track.artist_id == Artist.id)
            .outerjoin(Album, Track.album_id == Album.id)
            .outerjoin(LocalMedia, Track.id == LocalMedia.track_id)
            .options(
                joinedload(Track.media_files),
                joinedload(Track.artist),
                joinedload(Track.album),
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
