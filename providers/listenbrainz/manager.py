"""
ListenBrainz Metadata Provider
Manages caching of ListenBrainz playlists and metadata enrichment
"""

import json
from typing import List, Dict, Optional, Any
from datetime import datetime
from utils.logging_config import get_logger
from core.provider_base import ProviderBase
from core.job_queue import register_job
from database.music_database import get_database
from sdk.http_client import HttpClient, RetryConfig, RateLimitConfig
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = get_logger("listenbrainz_metadata_provider")


class ListenBrainzMetadataProvider(ProviderBase):
    """
    ListenBrainz metadata provider for caching playlists and enriching track metadata.
    Registered as a metadata provider in the plugin system.
    
    Properly inherits from ProviderBase and uses job_queue for periodic syncs.
    All database access goes through get_database() wrapper.
    """
    
    name = "listenbrainz"
    type = "provider"
    supports_downloads = False
    
    # Track field contracts
    provides_fields = [
        "album_cover_url",
        "release_mbid",
        "recording_mbid",
        "playlist_metadata"
    ]
    
    # Capabilities
    supports_cover_art = True
    supports_library_scan = False
    supports_streaming = False
    
    def __init__(self):
        """Initialize ListenBrainz provider"""
        from providers.listenbrainz.client import ListenBrainzClient
        self.client = ListenBrainzClient()
        
        # Initialize HTTP client for cover art fetching
        self._http = HttpClient(
            'listenbrainz_cover',
            retry=RetryConfig(max_retries=2),
            rate=RateLimitConfig(requests_per_second=5.0)
        )
        
        # Register as periodic job in job_queue
        register_job(
            name="listenbrainz_sync_playlists",
            func=self.sync_all_playlists,
            interval_seconds=3600,  # Run every hour
            max_retries=3,
            tags=["metadata", "listenbrainz"],
            plugin="listenbrainz"
        )
        
        logger.info("✅ ListenBrainz metadata provider initialized")
    
    # ========================================================================
    # ProviderBase Required Methods
    # ========================================================================
    
    def authenticate(self, **kwargs) -> bool:
        """Authenticate with ListenBrainz"""
        return self.client.is_authenticated()
    
    def search(self, query: str, type: str = "track", limit: int = 10) -> List[Dict[str, Any]]:
        """ListenBrainz doesn't support search"""
        return []
    
    def get_track(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Not implemented for ListenBrainz"""
        return None
    
    def get_album(self, album_id: str) -> Optional[Dict[str, Any]]:
        """Not implemented for ListenBrainz"""
        return None
    
    def get_artist(self, artist_id: str) -> Optional[Dict[str, Any]]:
        """Not implemented for ListenBrainz"""
        return None
    
    def get_user_playlists(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get user's ListenBrainz playlists"""
        try:
            playlists = self.client.get_user_playlists()
            return [{"id": p.get("identifier"), "title": p.get("title")} for p in playlists]
        except Exception as e:
            logger.error(f"Error fetching user playlists: {e}")
            return []
    
    def get_playlist_tracks(self, playlist_id: str) -> List[Dict[str, Any]]:
        """Get tracks from a cached playlist"""
        try:
            return self.get_cached_tracks(playlist_id)
        except Exception as e:
            logger.error(f"Error fetching playlist tracks: {e}")
            return []
    
    def is_configured(self) -> bool:
        """Check if provider is configured"""
        return self.client.is_authenticated()
    
    def get_logo_url(self) -> str:
        """Get provider logo URL"""
        return "https://listenbrainz.org/static/img/listenbrainz-logo.svg"
    
    # ========================================================================
    # Sync Methods (Periodic Jobs)
    # ========================================================================
    
    def sync_all_playlists(self) -> Dict[str, Any]:
        """
        Sync all ListenBrainz playlists to database.
        Called periodically by job_queue.
        """
        if not self.authenticate():
            logger.warning("ListenBrainz not authenticated, skipping sync")
            return {"success": False, "error": "Not authenticated"}
        
        logger.info("🔄 Syncing ListenBrainz playlists...")
        db = get_database()
        
        summary = {
            "created_for": {"updated": 0, "skipped": 0, "new": 0},
            "user": {"updated": 0, "skipped": 0, "new": 0},
            "collaborative": {"updated": 0, "skipped": 0, "new": 0}
        }
        
        playlist_types = [
            ("created_for", self.client.get_playlists_created_for_user),
            ("user", self.client.get_user_playlists),
            ("collaborative", self.client.get_collaborative_playlists)
        ]
        
        try:
            for playlist_type, fetch_func in playlist_types:
                try:
                    playlists = fetch_func()
                    logger.info(f"📋 Fetched {len(playlists)} {playlist_type} playlists")
                    
                    for playlist in playlists:
                        result = self._sync_playlist(db, playlist, playlist_type)
                        if result in summary[playlist_type]:
                            summary[playlist_type][result] += 1
                
                except Exception as e:
                    logger.error(f"Error syncing {playlist_type} playlists: {e}")
            
            # Cleanup old playlists
            self._cleanup_old_playlists(db)
            
            logger.info(f"✅ ListenBrainz sync complete: {summary}")
            return {"success": True, "summary": summary}
        
        except Exception as e:
            logger.error(f"Error during playlist sync: {e}")
            return {"success": False, "error": str(e)}
    
    def _sync_playlist(self, db, playlist_data: Dict, playlist_type: str) -> str:
        """Sync a single playlist to database"""
        try:
            # Extract playlist
            playlist = playlist_data.get('playlist', playlist_data)
            playlist_mbid = playlist.get('identifier', '').split('/')[-1]
            
            if not playlist_mbid:
                logger.warning("Playlist missing MBID, skipping")
                return "skipped"
            
            title = playlist.get('title', 'Untitled')
            creator = playlist.get('creator', 'Unknown')
            tracks = playlist.get('track', [])
            
            # If no tracks, fetch full details
            if not tracks:
                logger.debug(f"Fetching full details for '{title}'...")
                full = self.client.get_playlist_details(playlist_mbid)
                if full:
                    playlist = full.get('playlist', full)
                    tracks = playlist.get('track', [])
            
            track_count = len(tracks)
            
            # Check if exists in database
            cursor = db.conn.cursor()
            cursor.execute(
                "SELECT id, track_count FROM listenbrainz_playlists WHERE playlist_mbid = ?",
                (playlist_mbid,)
            )
            existing = cursor.fetchone()
            
            if existing:
                db_id, db_track_count = existing
                
                # Skip if unchanged
                if db_track_count == track_count:
                    logger.debug(f"✓ '{title}' unchanged, skipping")
                    return "skipped"
                
                logger.info(f"🔄 '{title}' updated ({db_track_count} → {track_count})")
                
                # Delete old tracks
                cursor.execute("DELETE FROM listenbrainz_tracks WHERE playlist_id = ?", (db_id,))
                
                # Update playlist
                cursor.execute("""
                    UPDATE listenbrainz_playlists
                    SET title = ?, creator = ?, track_count = ?, last_updated = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (title, creator, track_count, db_id))
                
                playlist_id = db_id
                result = "updated"
            
            else:
                logger.info(f"➕ New playlist '{title}'")
                
                # Insert new
                cursor.execute("""
                    INSERT INTO listenbrainz_playlists
                    (playlist_mbid, title, creator, playlist_type, track_count, annotation_data)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    playlist_mbid,
                    title,
                    creator,
                    playlist_type,
                    track_count,
                    json.dumps(playlist.get('annotation', {}))
                ))
                
                playlist_id = cursor.lastrowid
                result = "new"
            
            # Cache tracks
            if tracks and playlist_id:
                self._insert_tracks(db, playlist_id, tracks)
            
            db.conn.commit()
            return result
        
        except Exception as e:
            logger.error(f"Error syncing playlist: {e}")
            return "skipped"
    
    def _insert_tracks(self, db, playlist_id: int, tracks: List[Dict]):
        """Insert tracks for a playlist"""
        logger.info(f"🎵 Caching {len(tracks)} tracks with cover art...")
        
        # Extract track data
        track_data_list = []
        cursor = db.conn.cursor()
        
        for idx, track in enumerate(tracks):
            # Get MBIDs
            recording_mbid = None
            release_mbid = None
            
            for identifier in track.get('identifier', []):
                if 'musicbrainz.org/recording/' in identifier:
                    recording_mbid = identifier.split('/')[-1]
                    break
            
            # Check extension data for release MBID
            extension = track.get('extension', {})
            mb_data = extension.get('https://musicbrainz.org/doc/jspf#track', {})
            additional_metadata = mb_data.get('additional_metadata', {})
            release_mbid = additional_metadata.get('caa_release_mbid')
            
            # Insert track
            cursor.execute("""
                INSERT INTO listenbrainz_tracks
                (playlist_id, position, track_name, artist_name, album_name,
                 duration_ms, recording_mbid, release_mbid, additional_metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                playlist_id,
                idx + 1,
                track.get('title', 'Unknown'),
                track.get('creator', 'Unknown'),
                track.get('album', 'Unknown'),
                track.get('duration', 0),
                recording_mbid,
                release_mbid,
                json.dumps(mb_data)
            ))
            
            track_data_list.append({
                'id': cursor.lastrowid,
                'release_mbid': release_mbid,
                'position': idx
            })
        
        db.conn.commit()
        
        # Fetch cover art
        self._fetch_cover_art_parallel(db, track_data_list)
    
    def _fetch_cover_art_parallel(self, db, track_data_list: List[Dict]):
        """Fetch cover art for tracks in parallel"""
        def fetch_cover(track):
            release_mbid = track.get('release_mbid')
            if not release_mbid:
                return None
            
            try:
                url = f"https://coverartarchive.org/release/{release_mbid}"
                response = self._http.get(url, timeout=3)
                
                if response.status_code == 200:
                    data = response.json()
                    images = data.get('images', [])
                    
                    # Front cover
                    for img in images:
                        if img.get('front'):
                            return img.get('thumbnails', {}).get('small') or img.get('image')
                    
                    # First image
                    if images:
                        return images[0].get('thumbnails', {}).get('small') or images[0].get('image')
            except:
                pass
            
            return None
        
        # Fetch in parallel
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(fetch_cover, track): track
                for track in track_data_list
            }
            
            cursor = db.conn.cursor()
            for future in as_completed(futures):
                track = futures[future]
                try:
                    cover_url = future.result()
                    if cover_url:
                        cursor.execute(
                            "UPDATE listenbrainz_tracks SET album_cover_url = ? WHERE id = ?",
                            (cover_url, track['id'])
                        )
                except Exception as e:
                    logger.debug(f"Error fetching cover: {e}")
        
        db.conn.commit()
        covers_found = sum(1 for t in track_data_list if t.get('album_cover_url'))
        logger.info(f"✅ Fetched {covers_found}/{len(track_data_list)} cover URLs")
    
    def _cleanup_old_playlists(self, db):
        """Keep only 4 most recent playlists per type"""
        cursor = db.conn.cursor()
        
        for playlist_type in ['created_for', 'user', 'collaborative']:
            try:
                # Get old playlist IDs
                cursor.execute("""
                    SELECT id FROM listenbrainz_playlists
                    WHERE playlist_type = ?
                    ORDER BY last_updated DESC
                    LIMIT -1 OFFSET 4
                """, (playlist_type,))
                
                old_ids = [row[0] for row in cursor.fetchall()]
                
                if old_ids:
                    placeholders = ','.join('?' * len(old_ids))
                    cursor.execute(f"DELETE FROM listenbrainz_tracks WHERE playlist_id IN ({placeholders})", old_ids)
                    cursor.execute(f"DELETE FROM listenbrainz_playlists WHERE id IN ({placeholders})", old_ids)
                    logger.info(f"🗑️ Removed {len(old_ids)} old {playlist_type} playlists")
            
            except Exception as e:
                logger.error(f"Error cleaning {playlist_type}: {e}")
        
        db.conn.commit()
    
    # ========================================================================
    # Cache Query Methods
    # ========================================================================
    
    def get_cached_playlists(self, playlist_type: str) -> List[Dict]:
        """Get cached playlists of a specific type"""
        try:
            db = get_database()
            cursor = db.conn.cursor()
            
            cursor.execute("""
                SELECT id, playlist_mbid, title, creator, track_count, annotation_data, last_updated
                FROM listenbrainz_playlists
                WHERE playlist_type = ?
                ORDER BY last_updated DESC
                LIMIT 4
            """, (playlist_type,))
            
            playlists = []
            for row in cursor.fetchall():
                playlists.append({
                    "id": row[0],
                    "playlist_mbid": row[1],
                    "title": row[2],
                    "creator": row[3],
                    "track_count": row[4],
                    "annotation": json.loads(row[5]) if row[5] else {},
                    "last_updated": row[6]
                })
            
            return playlists
        except Exception as e:
            logger.error(f"Error fetching cached playlists: {e}")
            return []
    
    def has_cached_playlists(self) -> bool:
        """Check if there are cached playlists"""
        try:
            db = get_database()
            cursor = db.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM listenbrainz_playlists")
            count = cursor.fetchone()[0]
            return count > 0
        except Exception as e:
            logger.error(f"Error checking cache: {e}")
            return False
    
    def get_cached_tracks(self, playlist_mbid: str) -> List[Dict]:
        """Get cached tracks for a playlist"""
        try:
            db = get_database()
            cursor = db.conn.cursor()
            
            # Get playlist ID
            cursor.execute(
                "SELECT id FROM listenbrainz_playlists WHERE playlist_mbid = ?",
                (playlist_mbid,)
            )
            playlist_row = cursor.fetchone()
            
            if not playlist_row:
                return []
            
            playlist_id = playlist_row[0]
            
            # Get tracks
            cursor.execute("""
                SELECT track_name, artist_name, album_name, duration_ms,
                       recording_mbid, release_mbid, album_cover_url, additional_metadata
                FROM listenbrainz_tracks
                WHERE playlist_id = ?
                ORDER BY position ASC
            """, (playlist_id,))
            
            tracks = []
            for row in cursor.fetchall():
                tracks.append({
                    "track_name": row[0],
                    "artist_name": row[1],
                    "album_name": row[2],
                    "duration_ms": row[3],
                    "recording_mbid": row[4],
                    "release_mbid": row[5],
                    "album_cover_url": row[6],
                    "additional_metadata": json.loads(row[7]) if row[7] else {}
                })
            
            return tracks
        except Exception as e:
            logger.error(f"Error fetching cached tracks: {e}")
            return []

