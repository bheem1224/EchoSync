#!/usr/bin/env python3

import sqlite3
import json
import logging
import os
import re
import threading
import time
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
from utils.logging_config import get_logger
from core.matching_engine.soul_sync_track import SoulSyncTrack

logger = get_logger("music_database")

# Ensure the Crypto.Cipher module is installed and importable
try:
    from Crypto.Cipher import AES
except ImportError:
    logger.error("Crypto.Cipher module is not installed. Please install it using 'pip install pycryptodome'.")
    raise

# Import from core.models (the module file, not the package)
# Use explicit import to avoid conflict with core/models/ package
import importlib.util
spec = importlib.util.spec_from_file_location("core_models_file", str(Path(__file__).parent.parent / "core" / "models.py"))
core_models_file = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core_models_file)
Track = core_models_file.Track
DownloadStatus = core_models_file.DownloadStatus

# Import matching engine for enhanced similarity logic
try:
    from legacy.matching_engine import MusicMatchingEngine
    _matching_engine = MusicMatchingEngine()
except ImportError:
    logger.warning("Could not import MusicMatchingEngine, falling back to basic similarity")
    _matching_engine = None
# Temporarily enable debug logging for edition matching
logger.setLevel(logging.DEBUG)

@dataclass
class DatabaseArtist:
    id: int
    name: str
    thumb_url: Optional[str] = None
    genres: Optional[List[str]] = None
    summary: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class DatabaseAlbum:
    id: int
    artist_id: int
    title: str
    year: Optional[int] = None
    thumb_url: Optional[str] = None
    genres: Optional[List[str]] = None
    track_count: Optional[int] = None
    duration: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class DatabaseTrack:
    id: int
    album_id: int
    artist_id: int
    title: str
    track_number: Optional[int] = None
    duration: Optional[int] = None
    file_path: Optional[str] = None
    bitrate: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class DatabaseTrackWithMetadata:
    """Track with joined artist and album names for metadata comparison"""
    id: int
    album_id: int
    artist_id: int
    title: str
    artist_name: str
    album_title: str
    track_number: Optional[int] = None
    duration: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class WatchlistArtist:
    """Artist being monitored for new releases"""
    id: int
    spotify_artist_id: str
    artist_name: str
    date_added: datetime
    last_scan_timestamp: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    image_url: Optional[str] = None
    include_albums: bool = True
    include_eps: bool = True
    include_singles: bool = True

@dataclass
class SimilarArtist:
    """Similar artist recommendation from Spotify"""
    id: int
    source_artist_id: str  # Watchlist artist's database ID
    similar_artist_spotify_id: str
    similar_artist_name: str
    similarity_rank: int  # 1-10, where 1 is most similar
    occurrence_count: int  # How many watchlist artists share this similar artist
    last_updated: datetime

@dataclass
class DiscoveryTrack:
    """Track in the discovery pool for recommendations"""
    id: int
    spotify_track_id: str
    spotify_album_id: str
    spotify_artist_id: str
    track_name: str
    artist_name: str
    album_name: str
    album_cover_url: Optional[str]
    duration_ms: int
    popularity: int
    release_date: str
    is_new_release: bool  # Released within last 30 days
    track_data_json: str  # Full Spotify track object for modal
    added_date: datetime

@dataclass
class RecentRelease:
    """Recent album release from watchlist artist"""
    id: int
    watchlist_artist_id: int
    album_spotify_id: str
    album_name: str
    release_date: str
    album_cover_url: Optional[str]
    track_count: int
    added_date: datetime

class MusicDatabase:
    """SQLite database manager for SoulSync music library data"""
    
    def __init__(self, database_path: str = None):
        # Resolve database path: prefer SOULSYNC_DATA_DIR, fallback to provided or default
        data_dir = os.getenv("SOULSYNC_DATA_DIR")
        if database_path:
            resolved_path = Path(database_path)
        elif data_dir:
            resolved_path = Path(data_dir) / "music_library.db"
        else:
            resolved_path = Path("data") / "music_library.db"

        self.database_path = resolved_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Ensure writer queue for this DB and initialize database
        try:
            ensure_writer(str(self.database_path))
        except Exception:
            pass
        self._initialize_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a NEW database connection for each operation (thread-safe)"""
        connection = sqlite3.connect(str(self.database_path), timeout=30.0)
        connection.row_factory = sqlite3.Row
        # Enable foreign key constraints and WAL mode for better concurrency
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 30000")  # 30 second timeout
        return connection
    
    def _initialize_database(self):
        from .engine import execute_write
        
        def _init(cursor):
            # Artists table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS artists (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    thumb_url TEXT,
                    genres TEXT,  -- JSON array
                    summary TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Albums table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS albums (
                    id INTEGER PRIMARY KEY,
                    artist_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    year INTEGER,
                    thumb_url TEXT,
                    genres TEXT,  -- JSON array
                    track_count INTEGER,
                    duration INTEGER,  -- milliseconds
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (artist_id) REFERENCES artists (id) ON DELETE CASCADE
                )
            """)

            # Tracks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tracks (
                    id INTEGER PRIMARY KEY,
                    album_id INTEGER NOT NULL,
                    artist_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    track_number INTEGER,
                    duration INTEGER,  -- milliseconds
                    file_path TEXT,
                    bitrate INTEGER,
                    isrc TEXT,  -- International Standard Recording Code
                    musicbrainz_id TEXT,  -- MusicBrainz Recording ID
                    musicbrainz_album_id TEXT,  -- MusicBrainz Album ID
                    disc_number INTEGER,  -- Disc number for multi-disc albums
                    total_discs INTEGER,  -- Total discs in album
                    track_total INTEGER,  -- Total tracks on album
                    version TEXT,  -- Track version/edition
                    is_compilation INTEGER,  -- Boolean: is this a compilation track
                    file_format TEXT,  -- Audio format (MP3, FLAC, etc.)
                    quality_tags TEXT,  -- JSON array of quality indicators
                    sample_rate INTEGER,  -- Hz
                    bit_depth INTEGER,  -- Bits per sample
                    file_size INTEGER,  -- Bytes
                    featured_artists TEXT,  -- JSON array of featured artist names
                    fingerprint TEXT,  -- Audio fingerprint for identification
                    fingerprint_confidence REAL,  -- Confidence score 0.0-1.0
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (album_id) REFERENCES albums (id) ON DELETE CASCADE,
                    FOREIGN KEY (artist_id) REFERENCES artists (id) ON DELETE CASCADE
                )
            """)

            # Metadata table for storing system information like last refresh dates
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Wishlist table for storing failed download tracks for retry
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS wishlist_tracks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    spotify_track_id TEXT UNIQUE NOT NULL,
                    spotify_data TEXT NOT NULL,  -- JSON of full Spotify track data
                    failure_reason TEXT,
                    retry_count INTEGER DEFAULT 0,
                    last_attempted TIMESTAMP,
                    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source_type TEXT DEFAULT 'unknown',  -- 'playlist', 'album', 'manual'
                    source_info TEXT  -- JSON of source context (playlist name, album info, etc.)
                )
            """)

            # Watchlist table for storing artists to monitor for new releases
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS watchlist_artists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    spotify_artist_id TEXT UNIQUE NOT NULL,
                    artist_name TEXT NOT NULL,
                    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_scan_timestamp TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_albums_artist_id ON albums (artist_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracks_album_id ON tracks (album_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracks_artist_id ON tracks (artist_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracks_isrc ON tracks (isrc)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracks_musicbrainz ON tracks (musicbrainz_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_wishlist_spotify_id ON wishlist_tracks (spotify_track_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_watchlist_spotify_id ON watchlist_artists (spotify_artist_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_wishlist_date_added ON wishlist_tracks (date_added)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_artists_name ON artists (name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_albums_title ON albums (title)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracks_title ON tracks (title)")

            # Add server_source columns for multi-server support (migration)
            self._add_server_source_columns(cursor)

            # Migrate ID columns to support both integer (Plex) and string (Jellyfin) IDs
            self._migrate_id_columns_to_text(cursor)

            # Add discovery feature tables (migration)
            self._add_discovery_tables(cursor)

            # Add image_url column to watchlist_artists (migration)
            self._add_watchlist_artist_image_column(cursor)

            # Add album type filter columns to watchlist_artists (migration)
            self._add_watchlist_album_type_filters(cursor)

            # Add matching engine caching tables (migration)
            self._add_matching_cache_tables(cursor)

            # Canonical Track storage (Track-centric)
            self._add_canonical_tracks_table(cursor)

        try:
            # Run DB initialization on writer thread to avoid concurrent writes
            execute_write(str(self.database_path), _init)
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            # Don't raise - this is a migration, database can still function without it
    
    def _add_server_source_columns(self, cursor):
        """Ensure `server_source` column exists on key tables (idempotent)."""
        try:
            try:
                cursor.execute("ALTER TABLE artists ADD COLUMN server_source TEXT DEFAULT 'local'")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE albums ADD COLUMN server_source TEXT DEFAULT 'local'")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE tracks ADD COLUMN server_source TEXT DEFAULT 'local'")
            except Exception:
                pass
            # Add ISRC and MusicBrainz columns for global identifier matching
            try:
                cursor.execute("ALTER TABLE tracks ADD COLUMN isrc TEXT")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE tracks ADD COLUMN musicbrainz_id TEXT")
            except Exception:
                pass
        except Exception:
            # Swallow errors - migration should not block initialization
            pass

    def _migrate_id_columns_to_text(self, cursor):
        """Migrate ID columns from INTEGER to TEXT to support both Plex (int) and Jellyfin (GUID) IDs"""
        try:
            # Check if migration has already been applied by looking for a specific marker
            cursor.execute("SELECT value FROM metadata WHERE key = 'id_columns_migrated' LIMIT 1")
            migration_done = cursor.fetchone()
            
            if migration_done:
                logger.debug("ID columns migration already applied")
                return
            
            logger.info("Migrating ID columns to support both integer and string IDs...")
            
            # SQLite doesn't support changing column types directly, so we need to recreate tables
            # This is a complex migration - let's do it safely
            
            # Step 1: Create new tables with TEXT IDs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS artists_new (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    thumb_url TEXT,
                    genres TEXT,
                    summary TEXT,
                    server_source TEXT DEFAULT 'plex',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS albums_new (
                    id TEXT PRIMARY KEY,
                    artist_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    year INTEGER,
                    thumb_url TEXT,
                    genres TEXT,
                    track_count INTEGER,
                    duration INTEGER,
                    server_source TEXT DEFAULT 'plex',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (artist_id) REFERENCES artists_new (id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tracks_new (
                    id TEXT PRIMARY KEY,
                    album_id TEXT NOT NULL,
                    artist_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    track_number INTEGER,
                    duration INTEGER,
                    file_path TEXT,
                    bitrate INTEGER,
                    isrc TEXT,
                    musicbrainz_id TEXT,
                    musicbrainz_album_id TEXT,
                    disc_number INTEGER,
                    total_discs INTEGER,
                    track_total INTEGER,
                    version TEXT,
                    is_compilation INTEGER,
                    file_format TEXT,
                    quality_tags TEXT,
                    sample_rate INTEGER,
                    bit_depth INTEGER,
                    file_size INTEGER,
                    featured_artists TEXT,
                    fingerprint TEXT,
                    fingerprint_confidence REAL,
                    server_source TEXT DEFAULT 'plex',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (album_id) REFERENCES albums_new (id) ON DELETE CASCADE,
                    FOREIGN KEY (artist_id) REFERENCES artists_new (id) ON DELETE CASCADE
                )
            """)
            
            # Step 2: Copy existing data (converting INTEGER IDs to TEXT)
            cursor.execute("""
                INSERT INTO artists_new (id, name, thumb_url, genres, summary, server_source, created_at, updated_at)
                SELECT CAST(id AS TEXT), name, thumb_url, genres, summary, 
                       COALESCE(server_source, 'plex'), created_at, updated_at 
                FROM artists
            """)
            
            cursor.execute("""
                INSERT INTO albums_new (id, artist_id, title, year, thumb_url, genres, track_count, duration, server_source, created_at, updated_at)
                SELECT CAST(id AS TEXT), CAST(artist_id AS TEXT), title, year, thumb_url, genres, track_count, duration,
                       COALESCE(server_source, 'plex'), created_at, updated_at
                FROM albums
            """)
            
            cursor.execute("""
                INSERT INTO tracks_new (id, album_id, artist_id, title, track_number, duration, file_path, bitrate, 
                                        isrc, musicbrainz_id, server_source, created_at, updated_at)
                SELECT CAST(id AS TEXT), CAST(album_id AS TEXT), CAST(artist_id AS TEXT), title, track_number, duration, file_path, bitrate,
                       NULL, NULL, COALESCE(server_source, 'plex'), created_at, updated_at
                FROM tracks
            """)
            
            # Step 3: Drop old tables and rename new ones
            cursor.execute("DROP TABLE IF EXISTS tracks")
            cursor.execute("DROP TABLE IF EXISTS albums") 
            cursor.execute("DROP TABLE IF EXISTS artists")
            
            cursor.execute("ALTER TABLE artists_new RENAME TO artists")
            cursor.execute("ALTER TABLE albums_new RENAME TO albums")
            cursor.execute("ALTER TABLE tracks_new RENAME TO tracks")
            
            # Step 4: Recreate indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_albums_artist_id ON albums (artist_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracks_album_id ON tracks (album_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracks_artist_id ON tracks (artist_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_artists_server_source ON artists (server_source)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_albums_server_source ON albums (server_source)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracks_server_source ON tracks (server_source)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_artists_name ON artists (name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_albums_title ON albums (title)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracks_title ON tracks (title)")
            
            # Step 5: Mark migration as complete
            cursor.execute("""
                INSERT OR REPLACE INTO metadata (key, value, updated_at) 
                VALUES ('id_columns_migrated', 'true', CURRENT_TIMESTAMP)
            """)
            
            logger.info("ID columns migration completed successfully")
            
        except Exception as e:
            logger.error(f"Error migrating ID columns: {e}")
            # Don't raise - this is a migration, database can still function

    def _add_discovery_tables(self, cursor):
        """Add tables for discovery feature: similar artists, discovery pool, and recent releases"""
        try:
            # Similar Artists table - stores similar artists for each watchlist artist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS similar_artists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_artist_id TEXT NOT NULL,
                    similar_artist_spotify_id TEXT NOT NULL,
                    similar_artist_name TEXT NOT NULL,
                    similarity_rank INTEGER DEFAULT 1,
                    occurrence_count INTEGER DEFAULT 1,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(source_artist_id, similar_artist_spotify_id)
                )
            """)

            # Discovery Pool table - rotating pool of 1000-2000 tracks for recommendations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS discovery_pool (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    spotify_track_id TEXT UNIQUE NOT NULL,
                    spotify_album_id TEXT NOT NULL,
                    spotify_artist_id TEXT NOT NULL,
                    track_name TEXT NOT NULL,
                    artist_name TEXT NOT NULL,
                    album_name TEXT NOT NULL,
                    album_cover_url TEXT,
                    duration_ms INTEGER,
                    popularity INTEGER DEFAULT 0,
                    release_date TEXT,
                    is_new_release BOOLEAN DEFAULT 0,
                    track_data_json TEXT NOT NULL,
                    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Recent Releases table - tracks new releases from watchlist artists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recent_releases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    watchlist_artist_id INTEGER NOT NULL,
                    album_spotify_id TEXT NOT NULL,
                    album_name TEXT NOT NULL,
                    release_date TEXT NOT NULL,
                    album_cover_url TEXT,
                    track_count INTEGER DEFAULT 0,
                    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(watchlist_artist_id, album_spotify_id),
                    FOREIGN KEY (watchlist_artist_id) REFERENCES watchlist_artists (id) ON DELETE CASCADE
                )
            """)

            # Discovery Recent Albums cache - for discover page recent releases section
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS discovery_recent_albums (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    album_spotify_id TEXT NOT NULL UNIQUE,
                    album_name TEXT NOT NULL,
                    artist_name TEXT NOT NULL,
                    artist_spotify_id TEXT NOT NULL,
                    album_cover_url TEXT,
                    release_date TEXT NOT NULL,
                    album_type TEXT DEFAULT 'album',
                    cached_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Discovery Curated Playlists - store curated track selections for consistency
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS discovery_curated_playlists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    playlist_type TEXT NOT NULL UNIQUE,
                    track_ids_json TEXT NOT NULL,
                    curated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Discovery Pool Metadata - track when pool was last populated to prevent over-polling
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS discovery_pool_metadata (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    last_populated_timestamp TIMESTAMP NOT NULL,
                    track_count INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # ListenBrainz Playlists - cache playlists from ListenBrainz
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS listenbrainz_playlists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    playlist_mbid TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    creator TEXT,
                    playlist_type TEXT NOT NULL,
                    track_count INTEGER DEFAULT 0,
                    annotation_data TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    cached_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # ListenBrainz Tracks - cache tracks for each playlist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS listenbrainz_tracks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    playlist_id INTEGER NOT NULL,
                    position INTEGER NOT NULL,
                    track_name TEXT NOT NULL,
                    artist_name TEXT NOT NULL,
                    album_name TEXT NOT NULL,
                    duration_ms INTEGER DEFAULT 0,
                    recording_mbid TEXT,
                    release_mbid TEXT,
                    album_cover_url TEXT,
                    additional_metadata TEXT,
                    FOREIGN KEY (playlist_id) REFERENCES listenbrainz_playlists (id) ON DELETE CASCADE,
                    UNIQUE(playlist_id, position)
                )
            """)

            # NOTE: Account management tables (oauth_pkce_sessions, services, service_config, accounts)
            # have been moved to config.db where they belong. Do not recreate them here.

            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_similar_artists_source ON similar_artists (source_artist_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_similar_artists_spotify ON similar_artists (similar_artist_spotify_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_similar_artists_occurrence ON similar_artists (occurrence_count)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_discovery_pool_spotify_track ON discovery_pool (spotify_track_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_discovery_pool_artist ON discovery_pool (spotify_artist_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_discovery_pool_added_date ON discovery_pool (added_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_discovery_pool_is_new ON discovery_pool (is_new_release)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_recent_releases_watchlist ON recent_releases (watchlist_artist_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_recent_releases_date ON recent_releases (release_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_discovery_recent_albums_date ON discovery_recent_albums (release_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_listenbrainz_playlists_type ON listenbrainz_playlists (playlist_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_listenbrainz_playlists_mbid ON listenbrainz_playlists (playlist_mbid)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_listenbrainz_tracks_playlist ON listenbrainz_tracks (playlist_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_listenbrainz_tracks_position ON listenbrainz_tracks (playlist_id, position)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_discovery_recent_albums_artist ON discovery_recent_albums (artist_spotify_id)")

            # Add genres column to discovery_pool if it doesn't exist (migration)
            cursor.execute("PRAGMA table_info(discovery_pool)")
            discovery_pool_columns = [column[1] for column in cursor.fetchall()]

            if 'artist_genres' not in discovery_pool_columns:
                cursor.execute("ALTER TABLE discovery_pool ADD COLUMN artist_genres TEXT")
                logger.info("Added artist_genres column to discovery_pool table")

            logger.info("Discovery tables created successfully")

        except Exception as e:
            logger.error(f"Error creating discovery tables: {e}")
            # Don't raise - this is a migration, database can still function

    def _add_watchlist_artist_image_column(self, cursor):
        """Add image_url column to watchlist_artists table"""
        try:
            cursor.execute("PRAGMA table_info(watchlist_artists)")
            columns = [column[1] for column in cursor.fetchall()]

            if 'image_url' not in columns:
                cursor.execute("ALTER TABLE watchlist_artists ADD COLUMN image_url TEXT")
                logger.info("Added image_url column to watchlist_artists table")

        except Exception as e:
            logger.error(f"Error adding image_url column to watchlist_artists: {e}")
            # Don't raise - this is a migration, database can still function

    def _add_watchlist_album_type_filters(self, cursor):
        """Add album type filter columns to watchlist_artists table"""
        try:
            cursor.execute("PRAGMA table_info(watchlist_artists)")
            columns = [column[1] for column in cursor.fetchall()]

            columns_to_add = {
                'include_albums': ('INTEGER', '1'),     # 1 = True (include albums)
                'include_eps': ('INTEGER', '1'),        # 1 = True (include EPs)
                'include_singles': ('INTEGER', '1')     # 1 = True (include singles)
            }

            for column_name, (column_type, default_value) in columns_to_add.items():
                if column_name not in columns:
                    cursor.execute(f"ALTER TABLE watchlist_artists ADD COLUMN {column_name} {column_type} DEFAULT {default_value}")
                    logger.info(f"Added {column_name} column to watchlist_artists table")

        except Exception as e:
            logger.error(f"Error adding album type filter columns to watchlist_artists: {e}")
            # Don't raise - this is a migration, database can still function

    def _add_matching_cache_tables(self, cursor):
        """Create tables for matching engine caching and scoring"""
        try:
            # Parsed Tracks table - cache parsed track data from filenames
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS parsed_tracks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    raw_string TEXT NOT NULL UNIQUE,
                    parsed_json TEXT NOT NULL,  -- JSON serialized SoulSyncTrack
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ttl_expires_at TIMESTAMP
                )
            """)

            # Match Cache table - cache matching results with TTL
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS match_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_track_json TEXT NOT NULL,  -- JSON serialized source SoulSyncTrack
                    candidate_track_json TEXT NOT NULL,  -- JSON serialized candidate SoulSyncTrack
                    confidence_score REAL NOT NULL,
                    profile_name TEXT NOT NULL,  -- Profile used (EXACT_SYNC, DOWNLOAD_SEARCH, etc.)
                    matching_engine_version TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    UNIQUE(source_track_json, candidate_track_json, profile_name)
                )
            """)

            # Quality Profiles table - store user-defined quality preferences
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quality_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    weights_json TEXT NOT NULL,  -- JSON containing text_weight, duration_weight, quality_bonus, version_penalty, etc.
                    is_default BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Scoring Weights table - configurable scoring weights per profile
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scoring_weights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id INTEGER NOT NULL,
                    weight_name TEXT NOT NULL,  -- e.g., 'text_weight', 'duration_weight', 'quality_bonus', 'version_penalty'
                    weight_value REAL NOT NULL,
                    weight_description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (profile_id) REFERENCES quality_profiles (id) ON DELETE CASCADE,
                    UNIQUE(profile_id, weight_name)
                )
            """)

            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_parsed_tracks_raw_string ON parsed_tracks (raw_string)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_parsed_tracks_expires ON parsed_tracks (ttl_expires_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_match_cache_profile ON match_cache (profile_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_match_cache_expires ON match_cache (expires_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_match_cache_score ON match_cache (confidence_score)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_quality_profiles_name ON quality_profiles (name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_quality_profiles_default ON quality_profiles (is_default)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_scoring_weights_profile ON scoring_weights (profile_id)")

            logger.info("Matching cache tables created successfully")

        except Exception as e:
            logger.error(f"Error creating matching cache tables: {e}")
            # Don't raise - this is a migration, database can still function

    def _add_canonical_tracks_table(self, cursor):
        """Create Track-centric canonical storage if missing."""
        try:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS canonical_tracks (
                    track_id TEXT PRIMARY KEY,
                    title TEXT,
                    artists TEXT,                  -- JSON array
                    album TEXT,
                    duration_ms INTEGER,
                    isrc TEXT,
                    musicbrainz_recording_id TEXT,
                    acoustid TEXT,
                    provider_refs TEXT,            -- JSON object
                    download_status TEXT,
                    file_path TEXT,
                    file_format TEXT,
                    bitrate INTEGER,
                    confidence_score REAL,
                    album_artist TEXT,
                    track_number INTEGER,
                    disc_number INTEGER,
                    release_year INTEGER,
                    genres TEXT,                   -- JSON array
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )

            # Indexes for fast lookup by global identifiers and fuzzy title search
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_canonical_isrc ON canonical_tracks (isrc)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_canonical_mbid ON canonical_tracks (musicbrainz_recording_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_canonical_acoustid ON canonical_tracks (acoustid)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_canonical_title ON canonical_tracks (title)")

            logger.info("Canonical Track storage is ready")
        except Exception as e:
            logger.error(f"Error creating canonical_tracks table: {e}")
            # Don't raise - this is a migration, database can still function

    def close(self):
        """Close database connection (no-op since we create connections per operation)"""
        # Each operation creates and closes its own connection, so nothing to do here
        pass

    # ======================================================================
    # Adapter-friendly wrappers (canonical Track storage)
    # ======================================================================

    def create_track(self, track: Track) -> str:
        """Create a new canonical Track record and return its ID."""
        self.upsert_canonical_track(track)
        return track.track_id

    def update_track(self, track: Track) -> None:
        """Update an existing canonical Track record."""
        self.upsert_canonical_track(track)

    def get_track(self, track_id: str) -> Optional[Track]:
        """Fetch canonical Track by ID."""
        return self.get_canonical_track(track_id)

    def find_track_by_provider_ref(self, provider: str, provider_id: str) -> Optional[Track]:
        """Find canonical Track by provider reference."""
        return self.find_canonical_by_provider_ref(provider, provider_id)

    def find_track_by_isrc(self, isrc: str) -> Optional[Track]:
        """Find canonical Track by ISRC."""
        matches = self.search_canonical_by_ids(isrc=isrc)
        return matches[0] if matches else None

    def find_track_by_musicbrainz_id(self, mbid: str) -> Optional[Track]:
        """Find canonical Track by MusicBrainz recording ID."""
        matches = self.search_canonical_by_ids(musicbrainz_recording_id=mbid)
        return matches[0] if matches else None

    def fuzzy_match_tracks(self, title: str, artists: List[str], album: Optional[str] = None, threshold: float = 0.0) -> List[Track]:
        """Fuzzy match canonical tracks by title and optional artist; filter by confidence threshold."""
        artist_str = artists[0] if artists else None
        results = self.search_canonical_fuzzy(title=title, artist=artist_str, limit=25)
        if threshold > 0.0:
            results = [t for t in results if (t.confidence_score or 0.0) >= threshold]
        return results
    
    def get_statistics(self) -> Dict[str, int]:
        """Get database statistics for all servers (legacy method)"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(DISTINCT name) FROM artists")
                artist_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM albums")
                album_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM tracks")
                track_count = cursor.fetchone()[0]
                
                return {
                    'artists': artist_count,
                    'albums': album_count,
                    'tracks': track_count
                }
        except Exception as e:
            logger.error(f"Error getting database statistics: {e}")
            return {'artists': 0, 'albums': 0, 'tracks': 0}
    
    def get_statistics_for_server(self, server_source: str = None) -> Dict[str, int]:
        """Get database statistics filtered by server source"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                if server_source:
                    # Get counts for specific server (deduplicate by name like general count)
                    cursor.execute("SELECT COUNT(DISTINCT name) FROM artists WHERE server_source = ?", (server_source,))
                    artist_count = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT COUNT(*) FROM albums WHERE server_source = ?", (server_source,))
                    album_count = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT COUNT(*) FROM tracks WHERE server_source = ?", (server_source,))
                    track_count = cursor.fetchone()[0]
                else:
                    # Get total counts (all servers)
                    cursor.execute("SELECT COUNT(*) FROM artists")
                    artist_count = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT COUNT(*) FROM albums")
                    album_count = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT COUNT(*) FROM tracks")
                    track_count = cursor.fetchone()[0]
                
                return {
                    'artists': artist_count,
                    'albums': album_count,
                    'tracks': track_count
                }
        except Exception as e:
            logger.error(f"Error getting database statistics for {server_source}: {e}")
            return {'artists': 0, 'albums': 0, 'tracks': 0}
    
    def count_artists(self) -> int:
        """Get total count of artists in database"""
        stats = self.get_statistics()
        return stats.get('artists', 0)
    
    def count_albums(self) -> int:
        """Get total count of albums in database"""
        stats = self.get_statistics()
        return stats.get('albums', 0)
    
    def count_tracks(self) -> int:
        """Get total count of tracks in database"""
        stats = self.get_statistics()
        return stats.get('tracks', 0)
    
    def clear_all_data(self):
        """Clear all data from database (for full refresh) - DEPRECATED: Use clear_server_data instead"""
        try:
            from .engine import execute_write

            def _task(cursor):
                cursor.execute("DELETE FROM tracks")
                cursor.execute("DELETE FROM albums")
                cursor.execute("DELETE FROM artists")
                # Note: VACUUM cannot run inside transaction - will be done separately

            execute_write(str(self.database_path), _task)
            
            # VACUUM outside of transaction
            try:
                logger.info("Vacuuming database to reclaim disk space...")
                conn = self._get_connection()
                conn.commit()
                conn.execute("VACUUM")
                conn.close()
            except Exception as vacuum_err:
                logger.warning(f"Could not VACUUM database: {vacuum_err}")
            
            logger.info("All database data cleared and file compacted")

        except Exception as e:
            logger.error(f"Error clearing database: {e}")
            raise
    
    def clear_server_data(self, server_source: str):
        """Clear data for specific server only (server-aware full refresh)"""
        try:
            from .engine import execute_write
            
            deleted_counts = {'tracks': 0, 'albums': 0, 'artists': 0}

            def _task(cursor):
                cursor.execute("DELETE FROM tracks WHERE server_source = ?", (server_source,))
                deleted_counts['tracks'] = cursor.rowcount

                cursor.execute("DELETE FROM albums WHERE server_source = ?", (server_source,))
                deleted_counts['albums'] = cursor.rowcount

                cursor.execute("DELETE FROM artists WHERE server_source = ?", (server_source,))
                deleted_counts['artists'] = cursor.rowcount
                
                # Note: VACUUM cannot run inside a transaction - will be done separately

            execute_write(str(self.database_path), _task)
            
            # VACUUM outside of transaction to reclaim disk space
            should_vacuum = deleted_counts['tracks'] > 1000 or deleted_counts['albums'] > 100
            if should_vacuum:
                try:
                    logger.info("Vacuuming database to reclaim disk space...")
                    conn = self._get_connection()
                    # Ensure any active transaction is committed
                    conn.commit()
                    # Now VACUUM can run
                    conn.execute("VACUUM")
                    conn.close()
                except Exception as vacuum_err:
                    logger.warning(f"Could not VACUUM database: {vacuum_err}")

            logger.info(f"Cleared {server_source} data: {deleted_counts['artists']} artists, {deleted_counts['albums']} albums, {deleted_counts['tracks']} tracks")

        except Exception as e:
            logger.error(f"Error clearing {server_source} database data: {e}")
            raise
    
    def recreate_database_for_full_refresh(self):
        """Drop and recreate all tables with updated schema for true full refresh
        
        This is called when user wants to start completely fresh with latest schema.
        Unlike clear_server_data which only clears data, this drops and recreates tables
        to ensure all schema changes are applied.
        """
        try:
            from .engine import execute_write
            
            logger.info("[REFRESH] Starting full database recreation - dropping and recreating all tables with latest schema...")
            
            def _task(cursor):
                # Drop existing tables in dependency order (children before parents)
                tables_to_drop = [
                    'parsed_tracks', 'match_cache', 'quality_profiles', 'scoring_weights',
                    'canonical_tracks', 'listenbrainz_tracks', 'listenbrainz_playlists',
                    'discovery_curated_playlists', 'discovery_pool_metadata', 'discovery_recent_albums',
                    'discovery_pool', 'recent_releases', 'similar_artists',
                    'wishlist_tracks', 'watchlist_artists', 'metadata',
                    'tracks', 'albums', 'artists'
                ]
                
                for table in tables_to_drop:
                    try:
                        cursor.execute(f"DROP TABLE IF EXISTS {table}")
                        logger.debug(f"  Dropped table: {table}")
                    except Exception as e:
                        logger.debug(f"  Could not drop {table}: {e}")
                
                logger.info("  All tables dropped - recreating schema...")

            from .engine import execute_write
            execute_write(str(self.database_path), _task)
            
            # Now reinitialize to create fresh schema with all tables
            logger.info("  Reinitializing database with fresh schema...")
            self._initialize_database()
            
            logger.info("[OK] Full database recreation completed - ready for fresh data import")

        except Exception as e:
            logger.error(f"Error recreating database: {e}")
            raise
    
    def cleanup_orphaned_records(self) -> Dict[str, int]:
        """Remove artists and albums that have no associated tracks"""
        try:
            results = {'orphaned_artists_removed': 0, 'orphaned_albums_removed': 0}

            def _task(cursor):
                # Find orphaned artists (no tracks)
                cursor.execute("""
                    SELECT COUNT(*) FROM artists 
                    WHERE id NOT IN (SELECT DISTINCT artist_id FROM tracks WHERE artist_id IS NOT NULL)
                """)
                results['orphaned_artists_removed'] = cursor.fetchone()[0]

                # Find orphaned albums (no tracks)
                cursor.execute("""
                    SELECT COUNT(*) FROM albums 
                    WHERE id NOT IN (SELECT DISTINCT album_id FROM tracks WHERE album_id IS NOT NULL)
                """)
                results['orphaned_albums_removed'] = cursor.fetchone()[0]

                if results['orphaned_artists_removed'] > 0:
                    cursor.execute("""
                        DELETE FROM artists 
                        WHERE id NOT IN (SELECT DISTINCT artist_id FROM tracks WHERE artist_id IS NOT NULL)
                    """)
                    logger.info(f"🧹 Removed {results['orphaned_artists_removed']} orphaned artists")

                if results['orphaned_albums_removed'] > 0:
                    cursor.execute("""
                        DELETE FROM albums 
                        WHERE id NOT IN (SELECT DISTINCT album_id FROM tracks WHERE album_id IS NOT NULL)
                    """)
                    logger.info(f"🧹 Removed {results['orphaned_albums_removed']} orphaned albums")

            execute_write(str(self.database_path), _task)
            return results

        except Exception as e:
            logger.error(f"Error cleaning up orphaned records: {e}")
            return {'orphaned_artists_removed': 0, 'orphaned_albums_removed': 0}
    
    def get_bulk_operations(self):
        """
        Get BulkOperations helper for batch insert/update operations.
        Uses a fresh connection with global database lock for thread safety.
        
        Returns:
            BulkOperations instance configured with database lock
        """
        from .bulk_operations import BulkOperations
        conn = self._get_connection()
        # Use global _database_lock for thread safety across all bulk operations
        return BulkOperations(conn, lock=_database_lock)
    
    def bulk_update_content(self, artists: List[Any], albums: List[Any] = None, 
                           tracks: List[Any] = None, server_source: str = "plex") -> tuple[int, int, int]:
        """
        High-level bulk update method for content synchronization.
        Delegates to BulkOperations for efficient batch processing.
        
        Args:
            artists: List of artist objects to insert/update
            albums: Optional list of albums (if None, fetched from artists)
            tracks: Optional list of tracks (if None, fetched from albums)
            server_source: Source server type
        
        Returns:
            Tuple of (artists_count, albums_count, tracks_count)
        """
        bulk_ops = self.get_bulk_operations()
        
        try:
            artists_count = bulk_ops.bulk_insert_artists(artists, server_source)
            
            albums_count = 0
            tracks_count = 0
            
            # If albums/tracks not provided, fetch from artists
            if albums is None:
                for artist in artists:
                    try:
                        artist_id = str(artist.ratingKey)
                        artist_albums = list(artist.albums())
                        albums_count += bulk_ops.bulk_insert_albums(artist_albums, artist_id, server_source)
                        
                        # Get tracks from each album
                        for album in artist_albums:
                            album_id = str(album.ratingKey)
                            album_tracks = list(album.tracks())
                            tracks_count += bulk_ops.bulk_insert_tracks(album_tracks, album_id, artist_id, server_source)
                    except Exception as e:
                        logger.warning(f"Error processing artist {getattr(artist, 'title', 'Unknown')}: {e}")
            else:
                # Use provided albums/tracks
                for album in albums:
                    try:
                        album_id = str(album.ratingKey)
                        artist_id = str(album.parentRatingKey) if hasattr(album, 'parentRatingKey') else "unknown"
                        albums_count += bulk_ops.bulk_insert_albums([album], artist_id, server_source)
                        
                        if tracks is None:
                            album_tracks = list(album.tracks())
                            tracks_count += bulk_ops.bulk_insert_tracks(album_tracks, album_id, artist_id, server_source)
                    except Exception as e:
                        logger.warning(f"Error processing album: {e}")
                
                if tracks is not None:
                    for track in tracks:
                        try:
                            track_id = str(track.ratingKey)
                            album_id = str(track.parentRatingKey) if hasattr(track, 'parentRatingKey') else "unknown"
                            artist_id = str(track.grandparentRatingKey) if hasattr(track, 'grandparentRatingKey') else "unknown"
                            tracks_count += bulk_ops.bulk_insert_tracks([track], album_id, artist_id, server_source)
                        except Exception as e:
                            logger.warning(f"Error processing track: {e}")
            
            logger.info(f"Bulk update complete: {artists_count} artists, {albums_count} albums, {tracks_count} tracks")
            return (artists_count, albums_count, tracks_count)
            
        except Exception as e:
            logger.error(f"Error in bulk_update_content: {e}")
            return (0, 0, 0)
    
    # Artist operations
    def insert_or_update_artist(self, plex_artist) -> bool:
        """Insert or update artist from Plex artist object - DEPRECATED: Use insert_or_update_media_artist instead"""
        return self.insert_or_update_media_artist(plex_artist, server_source='plex')
    
    def insert_or_update_media_artist(self, artist_obj, server_source: str = 'plex') -> bool:
        """Insert or update artist from media server artist object (Plex or Jellyfin) with text normalization"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Convert artist ID to string (handles both Plex integer IDs and Jellyfin GUIDs)
                artist_id = str(artist_obj.ratingKey)
                raw_name = artist_obj.title
                
                # Use original name without normalization
                name = raw_name

                # Debug logging to see if normalization is working
                if raw_name != name:
                    logger.info(f"Artist name normalized: '{raw_name}' -> '{name}'")
                thumb_url = getattr(artist_obj, 'thumb', None)
                
                # Only preserve timestamps and flags from summary, not full biography
                full_summary = getattr(artist_obj, 'summary', None) or ''
                summary = None
                if full_summary:
                    # Extract only our tracking markers (timestamps and ignore flags)
                    import re
                    markers = []
                    
                    # Extract timestamp marker
                    timestamp_match = re.search(r'-updatedAt\d{4}-\d{2}-\d{2}', full_summary)
                    if timestamp_match:
                        markers.append(timestamp_match.group(0))
                    
                    # Extract ignore flag
                    if '-IgnoreUpdate' in full_summary:
                        markers.append('-IgnoreUpdate')
                    
                    # Only store markers, not full biography
                    summary = '\n\n'.join(markers) if markers else None
                
                # Get genres (handle both Plex and Jellyfin formats)
                genres = []
                if hasattr(artist_obj, 'genres') and artist_obj.genres:
                    genres = [genre.tag if hasattr(genre, 'tag') else str(genre) 
                             for genre in artist_obj.genres]
                
                genres_json = json.dumps(genres) if genres else None
                
                # Check if artist exists with this ID and server source
                cursor.execute("SELECT id FROM artists WHERE id = ? AND server_source = ?", (artist_id, server_source))
                exists = cursor.fetchone()
                
                if exists:
                    # Update existing artist
                    cursor.execute("""
                        UPDATE artists
                        SET name = ?, thumb_url = ?, genres = ?, summary = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ? AND server_source = ?
                    """, (name, thumb_url, genres_json, summary, artist_id, server_source))
                    logger.debug(f"Updated existing {server_source} artist: {name} (ID: {artist_id})")
                else:
                    # Insert new artist
                    cursor.execute("""
                        INSERT INTO artists (id, name, thumb_url, genres, summary, server_source)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (artist_id, name, thumb_url, genres_json, summary, server_source))
                    logger.debug(f"Inserted new {server_source} artist: {name} (ID: {artist_id})")

                conn.commit()
                rows_affected = cursor.rowcount
                if rows_affected == 0:
                    logger.warning(f"Database insertion returned 0 rows affected for {server_source} artist: {name} (ID: {artist_id})")

                return True
                
        except Exception as e:
            logger.error(f"Error inserting/updating {server_source} artist {getattr(artist_obj, 'title', 'Unknown')}: {e}")
            return False

    def _normalize_artist_name(self, name: str) -> str:
        """
        Normalize artist names to handle inconsistencies like quote variations.
        Converts Unicode smart quotes to ASCII quotes for consistency.
        """
        if not name:
            return name

        # Replace Unicode smart quotes with regular ASCII quotes
        normalized = name.replace('\u201c', '"').replace('\u201d', '"')  # Left and right double quotes
        normalized = normalized.replace('\u2018', "'").replace('\u2019', "'")  # Left and right single quotes
        normalized = normalized.replace('\u00ab', '"').replace('\u00bb', '"')  # « » guillemets

        return normalized
    
    def get_artist(self, artist_id: int) -> Optional[DatabaseArtist]:
        """Get artist by ID"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT * FROM artists WHERE id = ?", (artist_id,))
                row = cursor.fetchone()
                
                if row:
                    genres = json.loads(row['genres']) if row['genres'] else None
                    return DatabaseArtist(
                        id=row['id'],
                        name=row['name'],
                        thumb_url=row['thumb_url'],
                        genres=genres,
                        summary=row['summary'],
                        created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                        updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
                    )
                return None
                
        except Exception as e:
            logger.error(f"Error getting artist {artist_id}: {e}")
            return None
    
    # Album operations
    def insert_or_update_album(self, plex_album, artist_id: int) -> bool:
        """Insert or update album from Plex album object - DEPRECATED: Use insert_or_update_media_album instead"""
        return self.insert_or_update_media_album(plex_album, artist_id, server_source='plex')
    
    def insert_or_update_media_album(self, album_obj, artist_id: str, server_source: str = 'plex') -> bool:
        """Insert or update album from media server album object (Plex or Jellyfin) with text normalization"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Convert album ID to string (handles both Plex integer IDs and Jellyfin GUIDs)
            album_id = str(album_obj.ratingKey)
            
            # Use original title without normalization
            title = album_obj.title
            year = getattr(album_obj, 'year', None)
            thumb_url = getattr(album_obj, 'thumb', None)
            
            # Get track count and duration (handle different server attributes)
            track_count = getattr(album_obj, 'leafCount', None) or getattr(album_obj, 'childCount', None)
            duration = getattr(album_obj, 'duration', None)
            
            # Get genres (handle both Plex and Jellyfin formats)
            genres = []
            if hasattr(album_obj, 'genres') and album_obj.genres:
                genres = [genre.tag if hasattr(genre, 'tag') else str(genre) 
                         for genre in album_obj.genres]
            
            genres_json = json.dumps(genres) if genres else None
            
            # Check if album exists with this ID and server source
            cursor.execute("SELECT id FROM albums WHERE id = ? AND server_source = ?", (album_id, server_source))
            exists = cursor.fetchone()
            
            if exists:
                # Update existing album
                cursor.execute("""
                    UPDATE albums 
                    SET artist_id = ?, title = ?, year = ?, thumb_url = ?, genres = ?, 
                        track_count = ?, duration = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND server_source = ?
                """, (artist_id, title, year, thumb_url, genres_json, track_count, duration, album_id, server_source))
            else:
                # Insert new album
                cursor.execute("""
                    INSERT INTO albums (id, artist_id, title, year, thumb_url, genres, track_count, duration, server_source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (album_id, artist_id, title, year, thumb_url, genres_json, track_count, duration, server_source))
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error inserting/updating {server_source} album {getattr(album_obj, 'title', 'Unknown')}: {e}")
            return False
    
    def get_albums_by_artist(self, artist_id: int) -> List[DatabaseAlbum]:
        """Get all albums by artist ID"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM albums WHERE artist_id = ? ORDER BY year, title", (artist_id,))
            rows = cursor.fetchall()
            
            albums = []
            for row in rows:
                genres = json.loads(row['genres']) if row['genres'] else None
                albums.append(DatabaseAlbum(
                    id=row['id'],
                    artist_id=row['artist_id'],
                    title=row['title'],
                    year=row['year'],
                    thumb_url=row['thumb_url'],
                    genres=genres,
                    track_count=row['track_count'],
                    duration=row['duration'],
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                    updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
                ))
            
            return albums
            
        except Exception as e:
            logger.error(f"Error getting albums for artist {artist_id}: {e}")
            return []
    
    # Track operations
    def insert_or_update_soul_sync_track(
        self,
        soul_sync_track: SoulSyncTrack,
        album_id: str,
        artist_id: str,
        server_source: str = 'plex'
    ) -> bool:
        """Insert or update track from SoulSyncTrack object - NEW PRIMARY METHOD
        
        This is the clean, provider-agnostic way to insert tracks.
        Database layer NEVER sees raw provider objects - only SoulSyncTrack.
        
        Args:
            soul_sync_track: SoulSyncTrack object with all metadata
            album_id: Album ID this track belongs to
            artist_id: Artist ID for this track
            server_source: Source server type ('plex', 'jellyfin', etc.)
            
        Returns:
            True if insert/update succeeded, False otherwise
        """
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                # Set shorter timeout to prevent long locks
                cursor.execute("PRAGMA busy_timeout = 10000")  # 10 second timeout
                
                # Generate track ID from album+artist+title (provider will have set their own ID elsewhere if needed)
                track_id = f"{album_id}_{artist_id}_{soul_sync_track.title.replace(' ', '_')}"
                
                logger.info(f"[DB OPERATION] Attempting to insert/update track: {soul_sync_track.title}")
                cursor.execute("""
                    INSERT OR REPLACE INTO tracks 
                    (id, album_id, artist_id, title, track_number, duration, file_path, bitrate, 
                     isrc, musicbrainz_id, musicbrainz_album_id, disc_number, total_discs, track_total,
                     version, is_compilation, file_format, quality_tags, sample_rate, bit_depth, file_size,
                     featured_artists, fingerprint, fingerprint_confidence, server_source, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    track_id,
                    album_id,
                    artist_id,
                    soul_sync_track.title,
                    soul_sync_track.track_number,
                    soul_sync_track.duration_ms,
                    soul_sync_track.file_path,
                    soul_sync_track.bitrate,
                    soul_sync_track.isrc,
                    soul_sync_track.musicbrainz_id,
                    soul_sync_track.musicbrainz_album_id,
                    soul_sync_track.disc_number,
                    soul_sync_track.total_discs,
                    soul_sync_track.track_total,
                    soul_sync_track.version,
                    1 if soul_sync_track.is_compilation else 0,  # Convert bool to int
                    soul_sync_track.file_format,
                    json.dumps(soul_sync_track.quality_tags) if soul_sync_track.quality_tags else None,
                    soul_sync_track.sample_rate,
                    soul_sync_track.bit_depth,
                    soul_sync_track.file_size,
                    json.dumps(soul_sync_track.featured_artists) if soul_sync_track.featured_artists else None,
                    soul_sync_track.fingerprint,
                    soul_sync_track.fingerprint_confidence,
                    server_source
                ))
                logger.info(f"[DB SUCCESS] Track '{soul_sync_track.title}' inserted/updated successfully.")
                
                conn.commit()
                return True
                
            except Exception as e:
                retry_count += 1
                if "database is locked" in str(e).lower() and retry_count < max_retries:
                    logger.warning(f"Database locked on track '{soul_sync_track.title}', retrying {retry_count}/{max_retries}...")
                    time.sleep(0.1 * retry_count)  # Exponential backoff
                    continue
                else:
                    logger.error(f"Error inserting/updating {server_source} track {soul_sync_track.title}: {e}")
                    return False
        
        return False
    
    def insert_or_update_track(self, plex_track, album_id: int, artist_id: int) -> bool:
        """Insert or update track from Plex track object - DEPRECATED: Use insert_or_update_soul_sync_track instead"""
        # Delegate to provider adapter which should call insert_or_update_soul_sync_track
        # This exists only for backward compatibility
        from providers.plex.adapter import convert_plex_track_to_soulsync
        soul_sync_track = convert_plex_track_to_soulsync(plex_track)
        if not soul_sync_track:
            return False
        return self.insert_or_update_soul_sync_track(soul_sync_track, album_id, artist_id, server_source='plex')
    
    
    def insert_or_update_media_track(
        self, 
        track_obj, 
        album_id: str, 
        artist_id: str, 
        server_source: str = 'plex',
        isrc: str = None,
        musicbrainz_id: str = None,
        acoustid: str = None
    ) -> bool:
        """DEPRECATED: Insert or update track from media server track object with retry logic
        
        Use insert_or_update_soul_sync_track instead for clean architecture.
        This method kept for backward compatibility only.
        
        Args:
            track_obj: Media server track object (Plex/Jellyfin) - only basic attributes accessed
            album_id: Album ID this track belongs to
            artist_id: Artist ID for this track
            server_source: Source server type ('plex', 'jellyfin')
            isrc: International Standard Recording Code (optional, extracted by caller)
            musicbrainz_id: MusicBrainz Recording ID (optional, extracted by caller)
            acoustid: AcoustID (optional, extracted by caller)
        
        Note: This method still extracts from provider objects for backward compatibility.
        New code should use insert_or_update_soul_sync_track() instead.
        """
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                # Set shorter timeout to prevent long locks
                cursor.execute("PRAGMA busy_timeout = 10000")  # 10 second timeout
                
                # Convert track ID to string (handles both Plex integer IDs and Jellyfin GUIDs)
                track_id = str(track_obj.ratingKey)
                
                # Use original title without normalization
                title = track_obj.title
                
                track_number = getattr(track_obj, 'trackNumber', None)
                duration = getattr(track_obj, 'duration', None)
                
                # Get file path and media info (Plex-specific, Jellyfin may not have these)
                file_path = None
                bitrate = None
                if hasattr(track_obj, 'media') and track_obj.media:
                    media = track_obj.media[0] if track_obj.media else None
                    if media:
                        if hasattr(media, 'parts') and media.parts:
                            part = media.parts[0]
                            file_path = getattr(part, 'file', None)
                        bitrate = getattr(media, 'bitrate', None)
                
                # Use INSERT OR REPLACE to handle duplicate IDs gracefully
                cursor.execute("""
                    INSERT OR REPLACE INTO tracks 
                    (id, album_id, artist_id, title, track_number, duration, file_path, bitrate, 
                     isrc, musicbrainz_id, server_source, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (track_id, album_id, artist_id, title, track_number, duration, file_path, bitrate, 
                      isrc, musicbrainz_id, server_source))
                
                conn.commit()
                return True
                
            except Exception as e:
                retry_count += 1
                if "database is locked" in str(e).lower() and retry_count < max_retries:
                    logger.warning(f"Database locked on track '{getattr(track_obj, 'title', 'Unknown')}', retrying {retry_count}/{max_retries}...")
                    time.sleep(0.1 * retry_count)  # Exponential backoff
                    continue
                else:
                    logger.error(f"Error inserting/updating {server_source} track {getattr(track_obj, 'title', 'Unknown')}: {e}")
                    return False
        
        return False
    
    def track_exists(self, track_id) -> bool:
        """Check if a track exists in the database by ID (supports both int and string IDs)"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Convert to string to handle both Plex integers and Jellyfin GUIDs
            track_id_str = str(track_id)
            cursor.execute("SELECT 1 FROM tracks WHERE id = ? LIMIT 1", (track_id_str,))
            result = cursor.fetchone()
            
            return result is not None
            
        except Exception as e:
            logger.error(f"Error checking if track {track_id} exists: {e}")
            return False
    
    def track_exists_by_server(self, track_id, server_source: str) -> bool:
        """Check if a track exists in the database by ID and server source"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Convert to string to handle both Plex integers and Jellyfin GUIDs
            track_id_str = str(track_id)
            cursor.execute("SELECT 1 FROM tracks WHERE id = ? AND server_source = ? LIMIT 1", (track_id_str, server_source))
            result = cursor.fetchone()
            
            return result is not None
            
        except Exception as e:
            logger.error(f"Error checking if track {track_id} exists for server {server_source}: {e}")
            return False
    
    def get_track_by_id(self, track_id) -> Optional[DatabaseTrackWithMetadata]:
        """Get a track with artist and album names by ID (supports both int and string IDs)"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Convert to string to handle both Plex integers and Jellyfin GUIDs
            track_id_str = str(track_id)
            cursor.execute("""
                SELECT t.id, t.album_id, t.artist_id, t.title, t.track_number, 
                       t.duration, t.created_at, t.updated_at,
                       a.name as artist_name, al.title as album_title
                FROM tracks t
                JOIN artists a ON t.artist_id = a.id
                JOIN albums al ON t.album_id = al.id
                WHERE t.id = ?
            """, (track_id_str,))
            
            row = cursor.fetchone()
            if row:
                return DatabaseTrackWithMetadata(
                    id=row['id'],
                    album_id=row['album_id'],
                    artist_id=row['artist_id'],
                    title=row['title'],
                    artist_name=row['artist_name'],
                    album_title=row['album_title'],
                    track_number=row['track_number'],
                    duration=row['duration'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
            return None
            
        except Exception as e:
            logger.error(f"Error getting track {track_id}: {e}")
            return None
    
    def get_tracks_by_album(self, album_id: int) -> List[DatabaseTrack]:
        """Get all tracks by album ID"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM tracks WHERE album_id = ? ORDER BY track_number, title", (album_id,))
            rows = cursor.fetchall()
            
            tracks = []
            for row in rows:
                tracks.append(DatabaseTrack(
                    id=row['id'],
                    album_id=row['album_id'],
                    artist_id=row['artist_id'],
                    title=row['title'],
                    track_number=row['track_number'],
                    duration=row['duration'],
                    file_path=row['file_path'],
                    bitrate=row['bitrate'],
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                    updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
                ))
            
            return tracks
            
        except Exception as e:
            logger.error(f"Error getting tracks for album {album_id}: {e}")
            return []
    
    def search_artists(self, query: str, limit: int = 50) -> List[DatabaseArtist]:
        """Search artists by name"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM artists 
                WHERE name LIKE ? 
                ORDER BY name 
                LIMIT ?
            """, (f"%{query}%", limit))
            
            rows = cursor.fetchall()
            
            artists = []
            for row in rows:
                genres = json.loads(row['genres']) if row['genres'] else None
                artists.append(DatabaseArtist(
                    id=row['id'],
                    name=row['name'],
                    thumb_url=row['thumb_url'],
                    genres=genres,
                    summary=row['summary'],
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                    updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
                ))
            
            return artists
            
        except Exception as e:
            logger.error(f"Error searching artists with query '{query}': {e}")
            return []
    
    def search_tracks(self, title: str = "", artist: str = "", limit: int = 50, server_source: str = None) -> List[DatabaseTrack]:
        """Search tracks by title and/or artist name with Unicode-aware fuzzy matching"""
        try:
            if not title and not artist:
                return []
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # STRATEGY 1: Try basic SQL LIKE search first (fastest)
            basic_results = self._search_tracks_basic(cursor, title, artist, limit, server_source)
            
            if basic_results:
                logger.debug(f"🔍 Basic search found {len(basic_results)} results")
                return basic_results
            
            # STRATEGY 2: If basic search fails and we have Unicode support, try normalized search
            try:
                from unidecode import unidecode
                unicode_support = True
            except ImportError:
                unicode_support = False
            
            if unicode_support:
                normalized_results = self._search_tracks_unicode_fallback(cursor, title, artist, limit, server_source)
                if normalized_results:
                    logger.debug(f"🔍 Unicode fallback search found {len(normalized_results)} results")
                    return normalized_results
            
            # STRATEGY 3: Last resort - broader fuzzy search with Python filtering
            fuzzy_results = self._search_tracks_fuzzy_fallback(cursor, title, artist, limit)
            if fuzzy_results:
                logger.debug(f"🔍 Fuzzy fallback search found {len(fuzzy_results)} results")
            
            return fuzzy_results
            
        except Exception as e:
            logger.error(f"Error searching tracks with title='{title}', artist='{artist}': {e}")
            return []
    
    def _search_tracks_basic(self, cursor, title: str, artist: str, limit: int, server_source: str = None) -> List[DatabaseTrack]:
        """Basic SQL LIKE search - fastest method"""
        where_conditions = []
        params = []
        
        if title:
            where_conditions.append("tracks.title LIKE ?")
            params.append(f"%{title}%")
        
        if artist:
            where_conditions.append("artists.name LIKE ?")
            params.append(f"%{artist}%")
        
        # Add server filter if specified
        if server_source:
            where_conditions.append("tracks.server_source = ?")
            params.append(server_source)
        
        if not where_conditions:
            return []
        
        where_clause = " AND ".join(where_conditions)
        params.append(limit)
        
        cursor.execute(f"""
            SELECT tracks.*, artists.name as artist_name, albums.title as album_title
            FROM tracks
            JOIN artists ON tracks.artist_id = artists.id
            JOIN albums ON tracks.album_id = albums.id
            WHERE {where_clause}
            ORDER BY tracks.title, artists.name
            LIMIT ?
        """, params)
        
        return self._rows_to_tracks(cursor.fetchall())
    
    def _search_tracks_unicode_fallback(self, cursor, title: str, artist: str, limit: int, server_source: str = None) -> List[DatabaseTrack]:
        """Unicode-aware fallback search - tries normalized versions"""
        from unidecode import unidecode
        
        # Normalize search terms
        title_norm = unidecode(title).lower() if title else ""
        artist_norm = unidecode(artist).lower() if artist else ""
        
        # Try searching with normalized versions
        where_conditions = []
        params = []
        
        if title:
            where_conditions.append("LOWER(tracks.title) LIKE ?")
            params.append(f"%{title_norm}%")
        
        if artist:
            where_conditions.append("LOWER(artists.name) LIKE ?")
            params.append(f"%{artist_norm}%")
        
        # Add server filter if specified
        if server_source:
            where_conditions.append("tracks.server_source = ?")
            params.append(server_source)
        
        if not where_conditions:
            return []
        
        where_clause = " AND ".join(where_conditions)
        params.append(limit * 2)  # Get more results for filtering
        
        cursor.execute(f"""
            SELECT tracks.*, artists.name as artist_name, albums.title as album_title
            FROM tracks
            JOIN artists ON tracks.artist_id = artists.id
            JOIN albums ON tracks.album_id = albums.id
            WHERE {where_clause}
            ORDER BY tracks.title, artists.name
            LIMIT ?
        """, params)
        
        rows = cursor.fetchall()
        
        # Filter results with proper Unicode normalization
        filtered_tracks = []
        for row in rows:
            db_title_norm = unidecode(row['title'].lower()) if row['title'] else ""
            db_artist_norm = unidecode(row['artist_name'].lower()) if row['artist_name'] else ""
            
            title_matches = not title or title_norm in db_title_norm
            artist_matches = not artist or artist_norm in db_artist_norm
            
            if title_matches and artist_matches:
                filtered_tracks.append(row)
                if len(filtered_tracks) >= limit:
                    break
        
        return self._rows_to_tracks(filtered_tracks)
    
    def _search_tracks_fuzzy_fallback(self, cursor, title: str, artist: str, limit: int) -> List[DatabaseTrack]:
        """Broadest fuzzy search - partial word matching"""
        # Get broader results by searching for individual words
        search_terms = []
        if title:
            # Split title into words and search for each
            title_words = [w.strip() for w in title.lower().split() if len(w.strip()) >= 3]
            search_terms.extend(title_words)
        
        if artist:
            # Split artist into words and search for each
            artist_words = [w.strip() for w in artist.lower().split() if len(w.strip()) >= 3]
            search_terms.extend(artist_words)
        
        if not search_terms:
            return []
        
        # Build a query that searches for any of the words
        like_conditions = []
        params = []
        
        for term in search_terms[:5]:  # Limit to 5 terms to avoid too broad search
            like_conditions.append("(LOWER(tracks.title) LIKE ? OR LOWER(artists.name) LIKE ?)")
            params.extend([f"%{term}%", f"%{term}%"])
        
        if not like_conditions:
            return []
        
        where_clause = " OR ".join(like_conditions)
        params.append(limit * 3)  # Get more results for scoring
        
        cursor.execute(f"""
            SELECT tracks.*, artists.name as artist_name, albums.title as album_title
            FROM tracks
            JOIN artists ON tracks.artist_id = artists.id
            JOIN albums ON tracks.album_id = albums.id
            WHERE {where_clause}
            ORDER BY tracks.title, artists.name
            LIMIT ?
        """, params)
        
        rows = cursor.fetchall()
        
        # Score and filter results
        scored_results = []
        for row in rows:
            # Simple scoring based on how many search terms match
            score = 0
            db_title_lower = row['title'].lower()
            db_artist_lower = row['artist_name'].lower()
            
            for term in search_terms:
                if term in db_title_lower or term in db_artist_lower:
                    score += 1            
            if score > 0:
                scored_results.append((score, row))
        
       
        
        # Sort by score and take top results
        scored_results.sort(key=lambda x: x[0], reverse=True)
        top_rows = [row for score, row in scored_results[:limit]]
        
        return self._rows_to_tracks(top_rows)
    
    def _rows_to_tracks(self, rows) -> List[DatabaseTrack]:
        """Convert database rows to DatabaseTrack objects"""
        tracks = []
        for row in rows:
            track = DatabaseTrack(
                id=row['id'],
                album_id=row['album_id'],
                artist_id=row['artist_id'],
                title=row['title'],
                track_number=row['track_number'],
                duration=row['duration'],
                file_path=row['file_path'],
                bitrate=row['bitrate'],
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
            )
            # Add artist and album info for compatibility with Plex responses
            track.artist_name = row['artist_name']
            track.album_title = row['album_title']
            tracks.append(track)
        return tracks
    
    def search_albums(self, title: str = "", artist: str = "", limit: int = 50, server_source: Optional[str] = None) -> List[DatabaseAlbum]:
        """Search albums by title and/or artist name with fuzzy matching"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Build dynamic query based on provided parameters  
            where_conditions = []
            params = []
            
            if title:
                where_conditions.append("albums.title LIKE ?")
                params.append(f"%{title}%")
            
            if artist:
                where_conditions.append("artists.name LIKE ?")
                params.append(f"%{artist}%")
            
            if server_source:
                where_conditions.append("albums.server_source = ?")
                params.append(server_source)
            
            if not where_conditions:
                # If no search criteria, return empty list
                return []
            
            where_clause = " AND ".join(where_conditions)
            params.append(limit)
            
            cursor.execute(f"""
                SELECT albums.*, artists.name as artist_name
                FROM albums
                JOIN artists ON albums.artist_id = artists.id
                WHERE {where_clause}
                ORDER BY albums.title, artists.name
                LIMIT ?
            """, params)
            
            rows = cursor.fetchall()
            
            albums = []
            for row in rows:
                genres = json.loads(row['genres']) if row['genres'] else None
                album = DatabaseAlbum(
                    id=row['id'],
                    artist_id=row['artist_id'],
                    title=row['title'],
                    year=row['year'],
                    thumb_url=row['thumb_url'],
                    genres=genres,
                    track_count=row['track_count'],
                    duration=row['duration'],
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                    updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
                )
                # Add artist info for compatibility with Plex responses
                album.artist_name = row['artist_name']
                albums.append(album)
            
            return albums
            
        except Exception as e:
            logger.error(f"Error searching albums with title='{title}', artist='{artist}': {e}")
            return []
        


    def _get_artist_variations(self, artist_name: str) -> List[str]:
            """Returns a list of known variations for an artist's name."""
            variations = [artist_name]
            name_lower = artist_name.lower()

            # Add more aliases here in the future
            if "korn" in name_lower:
                if "KoЯn" not in variations:
                    variations.append("KoЯn")
                if "Korn" not in variations:
                    variations.append("Korn")
            
            # Return unique variations
            return list(set(variations))

    
    def check_track_exists(self, title: str, artist: str, confidence_threshold: float = 0.8, server_source: str = None) -> Tuple[Optional[DatabaseTrack], float]:
        """
        Check if a track exists in the database with enhanced fuzzy matching and confidence scoring.
        Now uses the same sophisticated matching approach as album checking for consistency.
        Returns (track, confidence) tuple where confidence is 0.0-1.0
        """
        try:
            # Generate title variations for better matching (similar to album approach)
            title_variations = self._generate_track_title_variations(title)
            
            logger.debug(f"🔍 Enhanced track matching for '{title}' by '{artist}': trying {len(title_variations)} variations")
            for i, var in enumerate(title_variations):
                logger.debug(f"  {i+1}. '{var}'")
            
            best_match = None
            best_confidence = 0.0
            
            # Try each title variation
            for title_variation in title_variations:
                # Search for potential matches with this variation
                potential_matches = []
                artist_variations = self._get_artist_variations(artist)
                for artist_variation in artist_variations:
                    potential_matches.extend(self.search_tracks(title=title_variation, artist=artist_variation, limit=20, server_source=server_source))
                
                if not potential_matches:
                    continue
                
                logger.debug(f"🎵 Found {len(potential_matches)} tracks for variation '{title_variation}'")
                
                # Score each potential match
                for track in potential_matches:
                    confidence = self._calculate_track_confidence(title, artist, track)
                    logger.debug(f"  🎯 '{track.title}' confidence: {confidence:.3f}")
                    
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = track
            
            # Return match only if it meets threshold
            if best_match and best_confidence >= confidence_threshold:
                logger.debug(f"✅ Enhanced track match found: '{title}' -> '{best_match.title}' (confidence: {best_confidence:.3f})")
                return best_match, best_confidence
            else:
                logger.debug(f"❌ No confident track match for '{title}' (best: {best_confidence:.3f}, threshold: {confidence_threshold})")
                return None, best_confidence
            
        except Exception as e:
            logger.error(f"Error checking track existence for '{title}' by '{artist}': {e}")
            return None, 0.0
    
    def check_album_exists(self, title: str, artist: str, confidence_threshold: float = 0.8) -> Tuple[Optional[DatabaseAlbum], float]:
        """
        Check if an album exists in the database with fuzzy matching and confidence scoring.
        Returns (album, confidence) tuple where confidence is 0.0-1.0
        """
        try:
            # Search for potential matches
            potential_matches = self.search_albums(title=title, artist=artist, limit=20)
            
            if not potential_matches:
                return None, 0.0
            
            # Simple confidence scoring based on string similarity
            def calculate_confidence(db_album: DatabaseAlbum) -> float:
                title_similarity = self._string_similarity(title.lower().strip(), db_album.title.lower().strip())
                artist_similarity = self._string_similarity(artist.lower().strip(), db_album.artist_name.lower().strip())
                
                # Weight title and artist equally for albums
                return (title_similarity * 0.5) + (artist_similarity * 0.5)
            
            # Find best match
            best_match = None
            best_confidence = 0.0
            
            for album in potential_matches:
                confidence = calculate_confidence(album)
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = album
            
            # Return match only if it meets threshold
            if best_confidence >= confidence_threshold:
                return best_match, best_confidence
            else:
                return None, best_confidence
            
        except Exception as e:
            logger.error(f"Error checking album existence for '{title}' by '{artist}': {e}")
            return None, 0.0
    
    def _string_similarity(self, s1: str, s2: str) -> float:
        """
        Calculate string similarity using enhanced matching engine logic if available,
        otherwise falls back to Levenshtein distance.
        Returns value between 0.0 (no similarity) and 1.0 (identical)
        """
        if s1 == s2:
            return 1.0
        
        if not s1 or not s2:
            return 0.0
        
        # Use enhanced similarity from matching engine if available
        if _matching_engine:
            return _matching_engine.similarity_score(s1, s2)
        
        # Simple Levenshtein distance implementation
        len1, len2 = len(s1), len(s2)
        if len1 < len2:
            s1, s2 = s2, s1
            len1, len2 = len2, len1
        
        if len2 == 0:
            return 0.0
        
        # Create matrix
        previous_row = list(range(len2 + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        max_len = max(len1, len2)
        distance = previous_row[-1]
        similarity = (max_len - distance) / max_len
        
        return max(0.0, similarity)
    
    def check_album_completeness(self, album_id: int, expected_track_count: Optional[int] = None) -> Tuple[int, int, bool]:
        """
        Check if we have all tracks for an album.
        Returns (owned_tracks, expected_tracks, is_complete)
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get actual track count in our database
            cursor.execute("SELECT COUNT(*) FROM tracks WHERE album_id = ?", (album_id,))
            owned_tracks = cursor.fetchone()[0]
            
            # Get expected track count from album table
            cursor.execute("SELECT track_count FROM albums WHERE id = ?", (album_id,))
            result = cursor.fetchone()
            
            if not result:
                return 0, 0, False
            
            stored_track_count = result[0]
            
            # Use provided expected count if available, otherwise use stored count
            expected_tracks = expected_track_count if expected_track_count is not None else stored_track_count
            
            # Determine completeness with refined thresholds
            if expected_tracks and expected_tracks > 0:
                completion_ratio = owned_tracks / expected_tracks
                # Complete: 90%+, Nearly Complete: 80-89%, Partial: <80%
                is_complete = completion_ratio >= 0.9 and owned_tracks > 0
            else:
                # Fallback: if we have any tracks, consider it owned
                is_complete = owned_tracks > 0
            
            return owned_tracks, expected_tracks or 0, is_complete
            
        except Exception as e:
            logger.error(f"Error checking album completeness for album_id {album_id}: {e}")
            return 0, 0, False
    
    def check_album_exists_with_completeness(self, title: str, artist: str, expected_track_count: Optional[int] = None, confidence_threshold: float = 0.8, server_source: Optional[str] = None) -> Tuple[Optional[DatabaseAlbum], float, int, int, bool]:
        """
        Check if an album exists in the database with completeness information.
        Enhanced to handle edition matching (standard <-> deluxe variants).
        Returns (album, confidence, owned_tracks, expected_tracks, is_complete)
        """
        try:
            # Try enhanced edition-aware matching first with expected track count for Smart Edition Matching
            album, confidence = self.check_album_exists_with_editions(title, artist, confidence_threshold, expected_track_count, server_source)
            
            if not album:
                return None, 0.0, 0, 0, False
            
            # Now check completeness
            owned_tracks, expected_tracks, is_complete = self.check_album_completeness(album.id, expected_track_count)
            
            return album, confidence, owned_tracks, expected_tracks, is_complete
            
        except Exception as e:
            logger.error(f"Error checking album existence with completeness for '{title}' by '{artist}': {e}")
            return None, 0.0, 0, 0, False
    
    def check_album_exists_with_editions(self, title: str, artist: str, confidence_threshold: float = 0.8, expected_track_count: Optional[int] = None, server_source: Optional[str] = None) -> Tuple[Optional[DatabaseAlbum], float]:
        """
        Enhanced album existence check that handles edition variants.
        Matches standard albums with deluxe/platinum/special editions and vice versa.
        """
        try:
            # Generate album title variations for edition matching
            title_variations = self._generate_album_title_variations(title)
            
            logger.debug(f"🔍 Edition matching for '{title}' by '{artist}': trying {len(title_variations)} variations")
            for i, var in enumerate(title_variations):
                logger.debug(f"  {i+1}. '{var}'")
            
            best_match = None
            best_confidence = 0.0
            
            for variation in title_variations:
                # Search for this variation
                albums = self.search_albums(title=variation, artist=artist, limit=10, server_source=server_source)
                
                if albums:
                    logger.debug(f"📀 Found {len(albums)} albums for variation '{variation}'")
                
                if not albums:
                    continue
                
                # Score each potential match with Smart Edition Matching
                for album in albums:
                    confidence = self._calculate_album_confidence(title, artist, album, expected_track_count)
                    logger.debug(f"  🎯 '{album.title}' confidence: {confidence:.3f}")
                    
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = album
            
            # Return match only if it meets threshold
            if best_match and best_confidence >= confidence_threshold:
                logger.debug(f"✅ Edition match found: '{title}' -> '{best_match.title}' (confidence: {best_confidence:.3f})")
                return best_match, best_confidence
            else:
                logger.debug(f"❌ No confident edition match for '{title}' (best: {best_confidence:.3f}, threshold: {confidence_threshold})")
                return None, best_confidence
                
        except Exception as e:
            logger.error(f"Error in edition-aware album matching for '{title}' by '{artist}': {e}")
            return None, 0.0
    
    def _generate_album_title_variations(self, title: str) -> List[str]:
        """Generate variations of album title to handle edition matching"""
        variations = [title]  # Always include original
        
        # Clean up the title
        title_lower = title.lower().strip()
        
        # Define edition patterns and their variations
        edition_patterns = {
            r'\s*\(deluxe\s*edition?\)': ['deluxe', 'deluxe edition'],
            r'\s*\(expanded\s*edition?\)': ['expanded', 'expanded edition'],
            r'\s*\(platinum\s*edition?\)': ['platinum', 'platinum edition'],
            r'\s*\(special\s*edition?\)': ['special', 'special edition'],
            r'\s*\(remastered?\)': ['remastered', 'remaster'],
            r'\s*\(anniversary\s*edition?\)': ['anniversary', 'anniversary edition'],
            r'\s*\(.*version\)': ['version'],
            r'\s+deluxe\s*edition?$': ['deluxe', 'deluxe edition'],
            r'\s+platinum\s*edition?$': ['platinum', 'platinum edition'],
            r'\s+special\s*edition?$': ['special', 'special edition'],
            r'\s*-\s*deluxe': ['deluxe'],
            r'\s*-\s*platinum\s*edition?': ['platinum', 'platinum edition'],
        }
        
        # Check if title contains any edition indicators
        base_title = title
        found_editions = []
        
        for pattern, edition_types in edition_patterns.items():
            if re.search(pattern, title_lower):
                # Remove the edition part to get base title
                base_title = re.sub(pattern, '', title, flags=re.IGNORECASE).strip()
                found_editions.extend(edition_types)
                break
        
        # Add base title (without edition markers)
        if base_title != title:
            variations.append(base_title)
        
        # If we found a base title, add common edition variants
        if base_title != title:
            # Add common deluxe/platinum/special variants
            common_editions = [
                'deluxe edition',
                'deluxe',
                'platinum edition',
                'platinum',
                'special edition', 
                'expanded edition',
                'remastered',
                'anniversary edition'
            ]
            
            for edition in common_editions:
                variations.extend([
                    f"{base_title} ({edition.title()})",
                    f"{base_title} ({edition})",
                    f"{base_title} - {edition.title()}",
                    f"{base_title} {edition.title()}",
                ])
        
        # If original title is base form, add edition variants  
        elif not any(re.search(pattern, title_lower) for pattern in edition_patterns.keys()):
            # This appears to be a base album, add deluxe variants
            common_editions = ['Deluxe Edition', 'Deluxe', 'Platinum Edition', 'Special Edition']
            for edition in common_editions:
                variations.extend([
                    f"{title} ({edition})",
                    f"{title} - {edition}",
                    f"{title} {edition}",
                ])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_variations = []
        for var in variations:
            var_clean = var.strip()
            if var_clean and var_clean.lower() not in seen:
                seen.add(var_clean.lower())
                unique_variations.append(var_clean)
        
        return unique_variations
    
    def _calculate_album_confidence(self, search_title: str, search_artist: str, db_album: DatabaseAlbum, expected_track_count: Optional[int] = None) -> float:
        """Calculate confidence score for album match with Smart Edition Matching"""
        try:
            # Simple confidence based on string similarity
            title_similarity = self._string_similarity(search_title.lower().strip(), db_album.title.lower().strip())
            artist_similarity = self._string_similarity(search_artist.lower().strip(), db_album.artist_name.lower().strip())
            
            # Also try with cleaned versions (removing edition markers)
            clean_search_title = self._clean_album_title_for_comparison(search_title)
            clean_db_title = self._clean_album_title_for_comparison(db_album.title)
            clean_title_similarity = self._string_similarity(clean_search_title, clean_db_title)
            
            # Use the best title similarity
            best_title_similarity = max(title_similarity, clean_title_similarity)
            
            # Weight: 50% title, 50% artist (equal weight to prevent false positives)
            # Also require minimum artist similarity to prevent matching wrong artists
            confidence = (best_title_similarity * 0.5) + (artist_similarity * 0.5)
            
            # Apply artist similarity penalty: if artist match is too low, drastically reduce confidence
            if artist_similarity < 0.6:  # Less than 60% artist match
                confidence *= 0.3  # Reduce confidence by 70%
            
            # Smart Edition Matching: Boost confidence if we found a "better" edition
            if expected_track_count and db_album.track_count and clean_title_similarity >= 0.8:
                # If the cleaned titles match well, check if this is an edition upgrade
                if db_album.track_count >= expected_track_count:
                    # Found same/better edition (e.g., Deluxe when searching for Standard)
                    edition_bonus = min(0.15, (db_album.track_count - expected_track_count) / expected_track_count * 0.1)
                    confidence += edition_bonus
                    logger.debug(f"  📀 Edition upgrade bonus: +{edition_bonus:.3f} ({db_album.track_count} >= {expected_track_count} tracks)")
                elif db_album.track_count < expected_track_count * 0.8:
                    # Found significantly smaller edition, apply penalty
                    edition_penalty = 0.1
                    confidence -= edition_penalty
                    logger.debug(f"  📀 Edition downgrade penalty: -{edition_penalty:.3f} ({db_album.track_count} << {expected_track_count} tracks)")
            
            return min(confidence, 1.0)  # Cap at 1.0
            
        except Exception as e:
            logger.error(f"Error calculating album confidence: {e}")
            return 0.0
    
    def _generate_track_title_variations(self, title: str) -> List[str]:
        """Generate variations of track title for better matching"""
        variations = [title]  # Always include original
        
        # IMPORTANT: Generate bracket/dash style variations for better matching
        # Convert "Track - Instrumental" to "Track (Instrumental)" and vice versa
        if ' - ' in title:
            # Convert dash style to parentheses style
            dash_parts = title.split(' - ', 1)
            if len(dash_parts) == 2:
                paren_version = f"{dash_parts[0]} ({dash_parts[1]})"
                variations.append(paren_version)
        
        if '(' in title and ')' in title:
            # Convert parentheses style to dash style
            dash_version = re.sub(r'\s*\(([^)]+)\)\s*', r' - \1', title)
            if dash_version != title:
                variations.append(dash_version)
        
        # Clean up the title
        title_lower = title.lower().strip()
        
        # Conservative track title variations - only remove clear noise, preserve meaningful differences
        track_patterns = [
            # Remove explicit/clean markers only
            r'\s*\(explicit\)',
            r'\s*\(clean\)',
            r'\s*\[explicit\]',
            r'\s*\[clean\]',
            # Remove featuring artists in parentheses
            r'\s*\(.*feat\..*\)',
            r'\s*\(.*featuring.*\)',
            r'\s*\(.*ft\..*\)',
            # Remove radio/TV edit markers
            r'\s*\(radio\s*edit\)',
            r'\s*\(tv\s*edit\)',
            r'\s*\[radio\s*edit\]',
            r'\s*\[tv\s*edit\]',
        ]
        
        # DO NOT remove remixes, versions, or content after dashes
        # These are meaningful distinctions that should not be collapsed
        
        for pattern in track_patterns:
            # Apply pattern to original title
            cleaned = re.sub(pattern, '', title, flags=re.IGNORECASE).strip()
            if cleaned and cleaned.lower() != title_lower and cleaned not in variations:
                variations.append(cleaned)
            
            # Apply pattern to lowercase version
            cleaned_lower = re.sub(pattern, '', title_lower, flags=re.IGNORECASE).strip()
            if cleaned_lower and cleaned_lower != title_lower:
                # Convert back to proper case
                cleaned_proper = cleaned_lower.title()
                if cleaned_proper not in variations:
                    variations.append(cleaned_proper)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_variations = []
        for var in variations:
            var_key = var.lower().strip()
            if var_key not in seen and var.strip():
                seen.add(var_key)
                unique_variations.append(var.strip())
        
        return unique_variations
    
    def _normalize_for_comparison(self, text: str) -> str:
        """Normalize text for comparison with Unicode accent handling"""
        if not text:
            return ""
        
        # Try to use unidecode for accent normalization, fallback to basic if not available
        try:
            from unidecode import unidecode
            # Convert accents: é→e, ñ→n, ü→u, etc.
            normalized = unidecode(text)
        except ImportError:
            # Fallback: basic normalization without accent handling
            normalized = text
            logger.warning("unidecode not available, accent matching may be limited")
        
        # Convert to lowercase and strip
        return normalized.lower().strip()
    
    def _calculate_track_confidence(self, search_title: str, search_artist: str, db_track: DatabaseTrack) -> float:
        """Calculate confidence score for track match with enhanced cleaning and Unicode normalization"""
        try:
            # Unicode-aware normalization for accent matching (é→e, ñ→n, etc.)
            search_title_norm = self._normalize_for_comparison(search_title)
            search_artist_norm = self._normalize_for_comparison(search_artist)
            db_title_norm = self._normalize_for_comparison(db_track.title)
            db_artist_norm = self._normalize_for_comparison(db_track.artist_name)
            
            # Debug logging for Unicode normalization
            if search_title != search_title_norm or search_artist != search_artist_norm or \
               db_track.title != db_title_norm or db_track.artist_name != db_artist_norm:
                logger.debug(f"🔤 Unicode normalization:")
                logger.debug(f"   Search: '{search_title}' → '{search_title_norm}' | '{search_artist}' → '{search_artist_norm}'")
                logger.debug(f"   Database: '{db_track.title}' → '{db_title_norm}' | '{db_track.artist_name}' → '{db_artist_norm}'")
            
            # Direct similarity with Unicode normalization
            title_similarity = self._string_similarity(search_title_norm, db_title_norm)
            artist_similarity = self._string_similarity(search_artist_norm, db_artist_norm)
            
            # Also try with cleaned versions (removing parentheses, brackets, etc.)
            clean_search_title = self._clean_track_title_for_comparison(search_title)
            clean_db_title = self._clean_track_title_for_comparison(db_track.title)
            clean_title_similarity = self._string_similarity(clean_search_title, clean_db_title)
            
            # Use the best title similarity (direct or cleaned)
            best_title_similarity = max(title_similarity, clean_title_similarity)
            
            # Weight: 50% title, 50% artist (equal weight to prevent false positives)
            # Also require minimum artist similarity to prevent matching wrong artists
            confidence = (best_title_similarity * 0.5) + (artist_similarity * 0.5)
            
            # Apply artist similarity penalty: if artist match is too low, drastically reduce confidence
            if artist_similarity < 0.6:  # Less than 60% artist match
                confidence *= 0.3  # Reduce confidence by 70%
            
            return confidence
            
        except Exception as e:
            logger.error(f"Error calculating track confidence: {e}")
            return 0.0
    
    def _clean_track_title_for_comparison(self, title: str) -> str:
        """Clean track title for comparison by normalizing brackets/dashes and removing noise"""
        cleaned = title.lower().strip()
        
        # STEP 1: Normalize bracket/dash styles for consistent matching
        # Convert all bracket styles to spaces for better matching
        cleaned = re.sub(r'\s*[\[\(]\s*', ' ', cleaned)  # Convert opening brackets/parens to space
        cleaned = re.sub(r'\s*[\]\)]\s*', ' ', cleaned)  # Convert closing brackets/parens to space
        cleaned = re.sub(r'\s*-\s*', ' ', cleaned)       # Convert dashes to spaces too
        
        # STEP 2: Remove clear noise patterns - very conservative approach
        patterns_to_remove = [
            r'\s*explicit\s*',      # Remove explicit markers (now without brackets)
            r'\s*clean\s*',         # Remove clean markers (now without brackets)  
            r'\s*feat\..*',         # Remove featuring (now without brackets)
            r'\s*featuring.*',      # Remove featuring (now without brackets)
            r'\s*ft\..*',           # Remove ft. (now without brackets)
            r'\s*edit\s*$',         # Remove "- edit" suffix only (specific case: "Reborn - edit" → "Reborn")
        ]
        
        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE).strip()
        
        # STEP 3: Clean up extra spaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    def _clean_album_title_for_comparison(self, title: str) -> str:
        """Clean album title by removing edition markers for comparison"""
        cleaned = title.lower()
        
        # Remove common edition patterns
        patterns = [
            r'\s*\(deluxe\s*edition?\)',
            r'\s*\(expanded\s*edition?\)', 
            r'\s*\(platinum\s*edition?\)',
            r'\s*\(special\s*edition?\)',
            r'\s*\(remastered?\)',
            r'\s*\(anniversary\s*edition?\)',
            r'\s*\(.*version\)',
            r'\s*-\s*deluxe\s*edition?',
            r'\s*-\s*platinum\s*edition?',
            r'\s+deluxe\s*edition?$',
            r'\s+platinum\s*edition?$',
        ]
        
        for pattern in patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()
    
    def get_library_artists(self, search_query: str = "", letter: str = "", page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """
        Get artists for the library page with search, filtering, and pagination

        Args:
            search_query: Search term to filter artists by name
            letter: Filter by first letter (a-z, #, or "" for all)
            page: Page number (1-based)
            limit: Number of results per page

        Returns:
            Dict containing artists list, pagination info, and total count
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Build WHERE clause
                where_conditions = []
                params = []

                if search_query:
                    where_conditions.append("LOWER(name) LIKE LOWER(?)")
                    params.append(f"%{search_query}%")

                if letter and letter != "all":
                    if letter == "#":
                        # Numbers and special characters
                        where_conditions.append("SUBSTR(UPPER(name), 1, 1) NOT GLOB '[A-Z]'")
                    else:
                        # Specific letter
                        where_conditions.append("UPPER(SUBSTR(name, 1, 1)) = UPPER(?)")
                        params.append(letter)

                # Get active server for filtering
                from config.settings import config_manager
                active_server = config_manager.get_active_media_server()

                # Add active server filter to where conditions
                where_conditions.append("a.server_source = ?")
                params.append(active_server)

                where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

                # Get total count (matching dashboard method)
                count_query = f"""
                    SELECT COUNT(*) as total_count
                    FROM artists a
                    WHERE {where_clause}
                """
                cursor.execute(count_query, params)
                total_count = cursor.fetchone()['total_count']

                # Get artists with pagination
                offset = (page - 1) * limit

                artists_query = f"""
                    SELECT
                        a.id,
                        a.name,
                        a.thumb_url,
                        a.genres,
                        COUNT(DISTINCT al.id) as album_count,
                        COUNT(DISTINCT t.id) as track_count
                    FROM artists a
                    LEFT JOIN albums al ON a.id = al.artist_id
                    LEFT JOIN tracks t ON al.id = t.album_id
                    WHERE {where_clause}
                    GROUP BY a.id, a.name, a.thumb_url, a.genres
                    ORDER BY a.name COLLATE NOCASE
                    LIMIT ? OFFSET ?
                """
                # No need for complex query params now
                query_params = params + [limit, offset]

                cursor.execute(artists_query, query_params)
                rows = cursor.fetchall()

                # Convert to artist objects
                artists = []
                for row in rows:
                    # Parse genres from GROUP_CONCAT result
                    genres_str = row['genres'] or ''
                    genres = []
                    if genres_str:
                        # Try to parse as JSON first (new format)
                        try:
                            import json
                            parsed_genres = json.loads(genres_str)
                            if isinstance(parsed_genres, list):
                                genres = parsed_genres
                            else:
                                genres = [str(parsed_genres)]
                        except (json.JSONDecodeError, ValueError):
                            # Fall back to comma-separated format (old format)
                            genre_set = set()
                            for genre in genres_str.split(','):
                                if genre and genre.strip():
                                    genre_set.add(genre.strip())
                            genres = list(genre_set)

                    artist = DatabaseArtist(
                        id=row['id'],
                        name=row['name'],
                        thumb_url=row['thumb_url'] if row['thumb_url'] else None,
                        genres=genres
                    )

                    # Add stats
                    artist_data = {
                        'id': artist.id,
                        'name': artist.name,
                        'image_url': artist.thumb_url,
                        'genres': artist.genres,
                        'album_count': row['album_count'] or 0,
                        'track_count': row['track_count'] or 0
                    }
                    artists.append(artist_data)

                # Calculate pagination info
                total_pages = (total_count + limit - 1) // limit
                has_prev = page > 1
                has_next = page < total_pages

                return {
                    'artists': artists,
                    'pagination': {
                        'page': page,
                        'limit': limit,
                        'total_count': total_count,
                        'total_pages': total_pages,
                        'has_prev': has_prev,
                        'has_next': has_next
                    }
                }

        except Exception as e:
            logger.error(f"Error getting library artists: {e}")
            return {
                'artists': [],
                'pagination': {
                    'page': 1,
                    'limit': limit,
                    'total_count': 0,
                    'total_pages': 0,
                    'has_prev': False,
                    'has_next': False
                }
            }

    def get_artist_discography(self, artist_id) -> Dict[str, Any]:
        """
        Get complete artist information and their releases from the database.
        This will be combined with Spotify data for the full discography view.

        Args:
            artist_id: The artist ID from the database (string or int)

        Returns:
            Dict containing artist info and their owned releases
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Get artist information
                cursor.execute("""
                    SELECT
                        id, name, thumb_url, genres, server_source
                    FROM artists
                    WHERE id = ?
                """, (artist_id,))

                artist_row = cursor.fetchone()

                if not artist_row:
                    return {
                        'success': False,
                        'error': f'Artist with ID {artist_id} not found'
                    }

                # Parse genres
                genres_str = artist_row['genres'] or ''
                genres = []
                if genres_str:
                    # Try to parse as JSON first (new format)
                    try:
                        import json
                        parsed_genres = json.loads(genres_str)
                        if isinstance(parsed_genres, list):
                            genres = parsed_genres
                        else:
                            genres = [str(parsed_genres)]
                    except (json.JSONDecodeError, ValueError):
                        # Fall back to comma-separated format (old format)
                        genre_set = set()
                        for genre in genres_str.split(','):
                            if genre and genre.strip():
                                genre_set.add(genre.strip())
                        genres = list(genre_set)

                # Get artist's albums with track counts and completion
                # Include albums from ALL artists with the same name (fixes duplicate artist issue)
                cursor.execute("""
                    SELECT
                        a.id,
                        a.title,
                        a.year,
                        a.track_count,
                        a.thumb_url,
                        COUNT(t.id) as owned_tracks
                    FROM albums a
                    LEFT JOIN tracks t ON a.id = t.album_id
                    WHERE a.artist_id IN (
                        SELECT id FROM artists
                        WHERE name = (SELECT name FROM artists WHERE id = ?)
                        AND server_source = (SELECT server_source FROM artists WHERE id = ?)
                    )
                    GROUP BY a.id, a.title, a.year, a.track_count, a.thumb_url
                    ORDER BY a.year DESC, a.title
                """, (artist_id, artist_id))

                album_rows = cursor.fetchall()

                # Process albums and categorize by type
                albums = []
                eps = []
                singles = []

                # Get total stats for the artist (including all artists with same name)
                cursor.execute("""
                    SELECT
                        COUNT(DISTINCT a.id) as album_count,
                        COUNT(DISTINCT t.id) as track_count
                    FROM albums a
                    LEFT JOIN tracks t ON a.id = t.album_id
                    WHERE a.artist_id IN (
                        SELECT id FROM artists
                        WHERE name = (SELECT name FROM artists WHERE id = ?)
                        AND server_source = (SELECT server_source FROM artists WHERE id = ?)
                    )
                """, (artist_id, artist_id))

                stats_row = cursor.fetchone()
                album_count = stats_row['album_count'] if stats_row else 0
                track_count = stats_row['track_count'] if stats_row else 0

                for album_row in album_rows:
                    # Calculate completion percentage
                    expected_tracks = album_row['track_count'] or 1
                    owned_tracks = album_row['owned_tracks'] or 0
                    completion_percentage = min(100, round((owned_tracks / expected_tracks) * 100))

                    album_data = {
                        'id': album_row['id'],
                        'title': album_row['title'],
                        'year': album_row['year'],
                        'image_url': album_row['thumb_url'],
                        'owned': True,  # All albums in our DB are owned
                        'track_count': album_row['track_count'],
                        'owned_tracks': owned_tracks,
                        'track_completion': completion_percentage
                    }

                    # Categorize based on actual track count and title patterns
                    # Use actual owned tracks, fallback to expected track count, then to 0
                    actual_track_count = owned_tracks or album_row['track_count'] or 0
                    title_lower = album_row['title'].lower()

                    # Check for single indicators in title
                    single_indicators = ['single', ' - single', '(single)']
                    is_single_by_title = any(indicator in title_lower for indicator in single_indicators)

                    # Check for EP indicators in title
                    ep_indicators = ['ep', ' - ep', '(ep)', 'extended play']
                    is_ep_by_title = any(indicator in title_lower for indicator in ep_indicators)

                    # Categorization logic - be more conservative about singles
                    # Only treat as single if explicitly labeled as single AND has few tracks
                    if is_single_by_title and actual_track_count <= 3:
                        singles.append(album_data)
                    elif is_ep_by_title or (4 <= actual_track_count <= 7):
                        eps.append(album_data)
                    else:
                        # Default to album for most releases, especially if track count is unknown
                        albums.append(album_data)

                # Fix image URLs if needed
                artist_image_url = artist_row['thumb_url']
                if artist_image_url and artist_image_url.startswith('/library/'):
                    # This will be fixed in the API layer
                    pass

                return {
                    'success': True,
                    'artist': {
                        'id': artist_row['id'],
                        'name': artist_row['name'],
                        'image_url': artist_image_url,
                        'genres': genres,
                        'server_source': artist_row['server_source'],
                        'album_count': album_count,
                        'track_count': track_count
                    },
                    'owned_releases': {
                        'albums': albums,
                        'eps': eps,
                        'singles': singles
                    }
                }

        except Exception as e:
            logger.error(f"Error getting artist discography for ID {artist_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    # ==========================================
    # OAuth PKCE Session Management
    # ==========================================

    def store_pkce_session(self, pkce_id: str, service: str, account_id: int, 
                          code_verifier: str, code_challenge: str, redirect_uri: str, 
                          client_id: str, ttl_seconds: int = 600) -> bool:
        """Store PKCE session in database with TTL"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            created_at = int(time.time())
            expires_at = created_at + ttl_seconds
            
            cursor.execute("""
                INSERT OR REPLACE INTO oauth_pkce_sessions 
                (pkce_id, service, account_id, code_verifier, code_challenge, 
                 redirect_uri, client_id, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (pkce_id, service, account_id, code_verifier, code_challenge,
                  redirect_uri, client_id, created_at, expires_at))
            
            conn.commit()
            conn.close()
            logger.info(f"Stored {service} PKCE session {pkce_id[:8]}... for account {account_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing PKCE session: {e}")
            return False
    
    def get_pkce_session(self, pkce_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve PKCE session from database"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT pkce_id, service, account_id, code_verifier, code_challenge,
                       redirect_uri, client_id, created_at, expires_at
                FROM oauth_pkce_sessions
                WHERE pkce_id = ?
            """, (pkce_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                logger.warning(f"PKCE session {pkce_id[:8]}... not found")
                return None
            
            # Check if expired
            if int(time.time()) >= row['expires_at']:
                logger.warning(f"PKCE session {pkce_id[:8]}... expired")
                self.delete_pkce_session(pkce_id)
                return None
            
            return {
                'pkce_id': row['pkce_id'],
                'service': row['service'],
                'account_id': row['account_id'],
                'code_verifier': row['code_verifier'],
                'code_challenge': row['code_challenge'],
                'redirect_uri': row['redirect_uri'],
                'client_id': row['client_id'],
                'created_at': row['created_at'],
                'expires_at': row['expires_at']
            }
            
        except Exception as e:
            logger.error(f"Error retrieving PKCE session: {e}")
            return None
    
    def delete_pkce_session(self, pkce_id: str) -> bool:
        """Delete PKCE session from database"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM oauth_pkce_sessions WHERE pkce_id = ?", (pkce_id,))
            
            conn.commit()
            conn.close()
            logger.info(f"Deleted PKCE session {pkce_id[:8]}...")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting PKCE session: {e}")
            return False
    
    def cleanup_expired_pkce_sessions(self) -> int:
        """Clean up expired PKCE sessions and return count of deleted sessions"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            current_time = int(time.time())
            cursor.execute("DELETE FROM oauth_pkce_sessions WHERE expires_at < ?", (current_time,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired PKCE sessions")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired PKCE sessions: {e}")
            return 0

    def save_oauth_tokens(self, service: str, account_id: int, access_token: str, 
                         refresh_token: Optional[str], expires_in: int, 
                         token_type: str = 'Bearer', scope: Optional[str] = None) -> bool:
        """Save OAuth tokens to database"""
        try:
            # Encrypt tokens
            encrypted_access_token = access_token
            encrypted_refresh_token = refresh_token
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            expires_at = int(time.time()) + expires_in
            updated_at = int(time.time())
            
            cursor.execute("""
                INSERT INTO oauth_tokens 
                (service, account_id, access_token, refresh_token, token_type, expires_at, scope, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(service, account_id) 
                DO UPDATE SET 
                    access_token=excluded.access_token,
                    refresh_token=excluded.refresh_token,
                    token_type=excluded.token_type,
                    expires_at=excluded.expires_at,
                    scope=excluded.scope,
                    updated_at=excluded.updated_at
            """, (service, account_id, encrypted_access_token, encrypted_refresh_token, 
                  token_type, expires_at, scope, updated_at))
            
            conn.commit()
            conn.close()
            logger.info(f"Saved encrypted {service} OAuth tokens for account {account_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving OAuth tokens: {e}")
            return False
    
    # ============ Modern Account Management API (v2) ============
    
    def register_service(self, name: str, display_name: str, service_type: str, 
                        description: str = "", is_plugin: bool = False) -> Optional[int]:
        """Register a new service (Spotify, TIDAL, Jellyfin, etc.)"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO services (name, display_name, service_type, description, is_plugin)
                    VALUES (?, ?, ?, ?, ?)
                """, (name, display_name, service_type, description, is_plugin))
                conn.commit()
                
                cursor.execute("SELECT id FROM services WHERE name = ?", (name,))
                result = cursor.fetchone()
                service_id = result[0] if result else None
                
                if service_id:
                    logger.info(f"Registered service: {name} (ID: {service_id})")
                return service_id
        except Exception as e:
            logger.error(f"Error registering service {name}: {e}")
            return None
    
    def set_service_config(self, service_id: int, config_key: str, config_value: str, 
                          is_sensitive: bool = False) -> bool:
        """Store service configuration (client_id, redirect_uri, etc.)"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO service_config (service_id, config_key, config_value, is_sensitive)
                    VALUES (?, ?, ?, ?)
                """, (service_id, config_key, config_value, is_sensitive))
                conn.commit()
                logger.debug(f"Set config {config_key} for service {service_id}")
                return True
        except Exception as e:
            logger.error(f"Error setting service config: {e}")
            return False
    
    def get_service_config(self, service_id: int, config_key: str) -> Optional[str]:
        """Retrieve service configuration"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT config_value FROM service_config 
                    WHERE service_id = ? AND config_key = ?
                """, (service_id, config_key))
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting service config: {e}")
            return None
    
    def create_account(self, service_id: int, account_name: Optional[str] = None, display_name: Optional[str] = None,
                      user_id: Optional[str] = None, account_email: Optional[str] = None, explicit_id: Optional[int] = None) -> Optional[int]:
        """Create a new account for a service.
        If explicit_id is provided, use it as the account's ID to align with external config IDs.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                display_name = display_name or account_name
                
                if explicit_id is not None:
                    cursor.execute("""
                        INSERT INTO accounts (id, service_id, account_name, display_name, user_id, account_email)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (explicit_id, service_id, account_name, display_name, user_id, account_email))
                else:
                    cursor.execute("""
                        INSERT INTO accounts (service_id, account_name, display_name, user_id, account_email)
                        VALUES (?, ?, ?, ?, ?)
                    """, (service_id, account_name, display_name, user_id, account_email))
                conn.commit()
                
                account_id = explicit_id if explicit_id is not None else cursor.lastrowid
                logger.info(f"Created account {account_name} for service {service_id} (ID: {account_id})")
                return account_id
        except Exception as e:
            logger.error(f"Error creating account: {e}")
            return None
    
    def get_accounts(self, service_id: Optional[int] = None, is_active: Optional[bool] = None) -> List[Dict[str, Any]]:
        """List all accounts, optionally filtered by service or active status"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                query = "SELECT id, service_id, account_name, display_name, user_id, account_email, is_active, is_authenticated, last_authenticated_at FROM accounts WHERE 1=1"
                params = []
                
                if service_id is not None:
                    query += " AND service_id = ?"
                    params.append(service_id)
                if is_active is not None:
                    query += " AND is_active = ?"
                    params.append(is_active)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                accounts = []
                for row in rows:
                    accounts.append({
                        'id': row[0],
                        'service_id': row[1],
                        'account_name': row[2],
                        'display_name': row[3],
                        'user_id': row[4],
                        'account_email': row[5],
                        'is_active': bool(row[6]),
                        'is_authenticated': bool(row[7]),
                        'last_authenticated_at': row[8]
                    })
                return accounts
        except Exception as e:
            logger.error(f"Error getting accounts: {e}")
            return []
    
    def save_account_token(self, account_id: int, access_token: str, refresh_token: Optional[str] = None,
                          token_type: str = 'Bearer', expires_at: Optional[int] = None, scope: Optional[str] = None) -> bool:
        """Save OAuth tokens for an account"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO account_tokens 
                    (account_id, access_token, refresh_token, token_type, expires_at, scope)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (account_id, access_token, refresh_token, token_type, expires_at, scope))
                conn.commit()
                
                logger.info(f"Saved tokens for account {account_id}")
                return True
        except Exception as e:
            logger.error(f"Error saving account token: {e}")
            return False

    def set_account_user_id(self, account_id: int, user_id: str) -> bool:
        """Update the user_id for an existing account."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE accounts SET user_id = ?, updated_at = strftime('%s','now')
                    WHERE id = ?
                """, (user_id, account_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error setting account user_id: {e}")
            return False
    
    def get_account_token(self, account_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve OAuth tokens for an account"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT access_token, refresh_token, token_type, expires_at, scope, created_at, updated_at
                    FROM oauth_tokens
                    WHERE service = ? AND account_id = ?
                """, (service, account_id))
                
                row = cursor.fetchone()
                conn.close()
                
                if not row:
                    logger.info(f"No {service} OAuth tokens found for account {account_id}")
                    return None
                
                # Direct access to the tokens
                access_token = row['access_token']
                refresh_token = row['refresh_token'] if row['refresh_token'] else None
            
                return {
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'token_type': row['token_type'],
                    'expires_at': row['expires_at'],
                    'scope': row['scope'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                }
            
        except Exception as e:
            logger.error(f"Error retrieving OAuth tokens: {e}")
            return None
    
    def delete_oauth_tokens(self, service: str, account_id: int) -> bool:
        """Delete OAuth tokens from database"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM oauth_tokens WHERE service = ? AND account_id = ?", 
                          (service, account_id))
            
            conn.commit()
            conn.close()
            logger.info(f"Deleted {service} OAuth tokens for account {account_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting OAuth tokens: {e}")
            return False

    # ======================================================================
    # Canonical Track storage (Track-centric)
    # ======================================================================

    def _row_to_canonical_track(self, row: sqlite3.Row) -> Track:
        """Convert canonical_tracks row to Track instance."""
        try:
            data = {
                'track_id': row['track_id'],
                'title': row['title'],
                'artists': json.loads(row['artists']) if row['artists'] else [],
                'album': row['album'],
                'duration_ms': row['duration_ms'],
                'isrc': row['isrc'],
                'musicbrainz_recording_id': row['musicbrainz_recording_id'],
                'acoustid': row['acoustid'],
                'provider_refs': json.loads(row['provider_refs']) if row['provider_refs'] else {},
                'download_status': row['download_status'] or DownloadStatus.MISSING.value,
                'file_path': row['file_path'],
                'file_format': row['file_format'],
                'bitrate': row['bitrate'],
                'confidence_score': row['confidence_score'] if row['confidence_score'] is not None else 0.0,
                'album_artist': row['album_artist'],
                'track_number': row['track_number'],
                'disc_number': row['disc_number'],
                'release_year': row['release_year'],
                'genres': json.loads(row['genres']) if row['genres'] else [],
                'created_at': row['created_at'] or datetime.now().isoformat(),
                'updated_at': row['updated_at'] or datetime.now().isoformat(),
            }
            return Track.from_dict(data)
        except Exception as e:
            logger.error(f"Error converting canonical track row: {e}")
            raise

    def upsert_canonical_track(self, track: Track) -> Track:
        """Insert or update a canonical Track record and return the stored Track."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Ensure timestamps are set
            now_iso = datetime.now().isoformat()
            track.created_at = track.created_at or datetime.now()
            track.updated_at = datetime.now()

            payload = track.to_dict()

            artists_json = json.dumps(payload['artists']) if payload.get('artists') is not None else json.dumps([])
            provider_refs_json = json.dumps(payload['provider_refs']) if payload.get('provider_refs') is not None else json.dumps({})
            genres_json = json.dumps(payload['genres']) if payload.get('genres') is not None else json.dumps([])

            cursor.execute(
                """
                INSERT INTO canonical_tracks (
                    track_id, title, artists, album, duration_ms, isrc,
                    musicbrainz_recording_id, acoustid, provider_refs, download_status,
                    file_path, file_format, bitrate, confidence_score, album_artist,
                    track_number, disc_number, release_year, genres, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,)
                ON CONFLICT(track_id) DO UPDATE SET
                    title=excluded.title,
                    artists=excluded.artists,
                    album=excluded.album,
                    duration_ms=excluded.duration_ms,
                    isrc=excluded.isrc,
                    musicbrainz_recording_id=excluded.musicbrainz_recording_id,
                    acoustid=excluded.acoustid,
                    provider_refs=excluded.provider_refs,
                    download_status=excluded.download_status,
                    file_path=excluded.file_path,
                    file_format=excluded.file_format,
                    bitrate=excluded.bitrate,
                    confidence_score=excluded.confidence_score,
                    album_artist=excluded.album_artist,
                    track_number=excluded.track_number,
                    disc_number=excluded.disc_number,
                    release_year=excluded.release_year,
                    genres=excluded.genres,
                    updated_at=excluded.updated_at
                """,
                (
                    payload['track_id'],
                    payload.get('title'),
                    artists_json,
                    payload.get('album'),
                    payload.get('duration_ms'),
                    payload.get('isrc'),
                    payload.get('musicbrainz_recording_id'),
                    payload.get('acoustid'),
                    provider_refs_json,
                    payload.get('download_status', DownloadStatus.MISSING.value),
                    payload.get('file_path'),
                    payload.get('file_format'),
                    payload.get('bitrate'),
                    payload.get('confidence_score', 0.0),
                    payload.get('album_artist'),
                    payload.get('track_number'),
                    payload.get('disc_number'),
                    payload.get('release_year'),
                    genres_json,
                    payload.get('created_at', now_iso),
                    now_iso,
                ),
            )

            conn.commit()
            conn.close()
            return track
        except Exception as e:
            logger.error(f"Error upserting canonical track {track.track_id}: {e}")
            raise

    def get_canonical_track(self, track_id: str) -> Optional[Track]:
        """Fetch a canonical Track by ID."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM canonical_tracks WHERE track_id = ?", (track_id,))
            row = cursor.fetchone()
            conn.close()
            if not row:
                return None
            return self._row_to_canonical_track(row)
        except Exception as e:
            logger.error(f"Error fetching canonical track {track_id}: {e}")
            return None

    def delete_canonical_track(self, track_id: str) -> bool:
        """Delete a canonical Track by ID."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM canonical_tracks WHERE track_id = ?", (track_id,))
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting canonical track {track_id}: {e}")
            return False

    def search_canonical_by_ids(
        self,
        isrc: Optional[str] = None,
        musicbrainz_recording_id: Optional[str] = None,
        acoustid: Optional[str] = None,
    ) -> List[Track]:
        """Search canonical tracks by global identifiers (ISRC, MBID, AcoustID)."""
        clauses = []
        params: List[Any] = []

        if isrc:
            clauses.append("isrc = ?")
            params.append(isrc)
        if musicbrainz_recording_id:
            clauses.append("musicbrainz_recording_id = ?")
            params.append(musicbrainz_recording_id)
        if acoustid:
            clauses.append("acoustid = ?")
            params.append(acoustid)

        if not clauses:
            return []

        query = "SELECT * FROM canonical_tracks WHERE " + " OR ".join(clauses)
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            conn.close()
            return [self._row_to_canonical_track(row) for row in rows]
        except Exception as e:
            logger.error(f"Error searching canonical tracks by IDs: {e}")
            return []

    def find_canonical_by_provider_ref(self, provider: str, provider_id: str) -> Optional[Track]:
        """Find a canonical track by provider reference (JSON search)."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            pattern = f'%"provider_id": "{provider_id}"%'
            provider_pattern = f'%"provider": "{provider}"%'
            cursor.execute(
                "SELECT * FROM canonical_tracks WHERE provider_refs LIKE ? AND provider_refs LIKE ? LIMIT 1",
                (pattern, provider_pattern),
            )
            row = cursor.fetchone()
            conn.close()
            if not row:
                return None
            return self._row_to_canonical_track(row)
        except Exception as e:
            logger.error(f"Error finding canonical track by provider ref {provider}:{provider_id}: {e}")
            return None

    def search_canonical_fuzzy(self, title: str, artist: Optional[str] = None, limit: int = 10) -> List[Track]:
        """Fuzzy search canonical tracks by title and optional artist substring."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            title_like = f"%{title}%"
            if artist:
                artist_like = f"%{artist}%"
                cursor.execute(
                    """
                    SELECT * FROM canonical_tracks
                    WHERE title LIKE ? AND artists LIKE ?
                    ORDER BY confidence_score DESC, updated_at DESC
                    LIMIT ?
                    """,
                    (title_like, artist_like, limit),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM canonical_tracks
                    WHERE title LIKE ?
                    ORDER BY confidence_score DESC, updated_at DESC
                    LIMIT ?
                    """,
                    (title_like, limit),
                )
            rows = cursor.fetchall()
            conn.close()
            return [self._row_to_canonical_track(row) for row in rows]
        except Exception as e:
            logger.error(f"Error performing fuzzy search on canonical tracks: {e}")
            return []