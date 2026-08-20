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
from core.matching_engine.text_utils import normalize_text, normalize_title, normalize_track_comparison_fields
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
    1. Dual artist matching: Matches Track.artist, Artist.name, Artist.sort_name,
       and Album.artist (including tracks filed under 'Various Artists' compilations).
    2. Multi-candidate retention: Returns all matching local media records for the
       (artist, title) tuple so downstream matching engines can evaluate durations
       for both original cuts and remixes simultaneously.
    
    Args:
        session: SQLAlchemy Session
        target_title: Target track title
        target_artist: Target track artist
        
    Returns:
        List of candidate Track records with loaded media_files, artist, and album.
    """
    clean_title = normalize_title_for_search(target_title)
    clean_artist = normalize_artist_for_search(target_artist)
    raw_title_clean = (target_title or "").strip()
    raw_artist_clean = (target_artist or "").strip()

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

    # Match Track Artist, Artist sort_name, or Album Artist (handles Various Artists compilations)
    artist_filter = or_(
        Artist.normalized_name == clean_artist,
        Artist.name.ilike(f"%{clean_artist}%"),
        Artist.name.ilike(f"%{raw_artist_clean}%"),
        Artist.sort_name.ilike(f"%{clean_artist}%"),
        Artist.sort_name.ilike(f"%{raw_artist_clean}%"),
    )

    query = (
        session.query(Track)
        .join(Artist, Track.artist_id == Artist.id)
        .outerjoin(Album, Track.album_id == Album.id)
        .outerjoin(LocalMedia, Track.id == LocalMedia.track_id)
        .options(
            selectinload(Track.media_files),
            joinedload(Track.artist),
            joinedload(Track.album),
        )
        .filter(title_filter, artist_filter)
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
                selectinload(Track.media_files),
                joinedload(Track.artist),
                joinedload(Track.album),
            )
            .filter(title_filter)
            .distinct()
            .limit(50)
        )
        candidates = fallback_query.all()

    return candidates
