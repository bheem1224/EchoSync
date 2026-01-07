"""
Bulk database operations for efficient batch inserts and updates.
Provides high-performance methods for synchronizing large amounts of content.
"""
import sqlite3
from typing import List, Any, Optional
from contextlib import contextmanager
from utils.logging_config import get_logger

logger = get_logger("bulk_operations")


class BulkOperations:
    """
    Provides batch insert/update operations with transaction safety.
    All methods use INSERT OR REPLACE for conflict resolution.
    """
    
    def __init__(self, connection: sqlite3.Connection, lock=None):
        """
        Initialize bulk operations handler.
        
        Args:
            connection: Active SQLite connection
            lock: Optional threading.Lock for thread-safe operations
        """
        self.conn = connection
        self.lock = lock
    
    @contextmanager
    def _transaction(self):
        """Context manager for safe transactions with optional locking"""
        if self.lock:
            with self.lock:
                try:
                    yield
                    self.conn.commit()
                except Exception as e:
                    self.conn.rollback()
                    logger.error(f"Transaction failed, rolling back: {e}")
                    raise
        else:
            try:
                yield
                self.conn.commit()
            except Exception as e:
                self.conn.rollback()
                logger.error(f"Transaction failed, rolling back: {e}")
                raise
    
    def bulk_insert_artists(self, artists: List[Any], server_source: str = "plex") -> int:
        """
        Bulk insert or update artists with conflict resolution.
        
        Args:
            artists: List of artist objects (Plex/Jellyfin/Navidrome artist objects)
            server_source: Source server type ('plex', 'jellyfin', 'navidrome')
        
        Returns:
            Number of artists inserted/updated
        """
        if not artists:
            return 0
        
        try:
            with self._transaction():
                cursor = self.conn.cursor()
                count = 0
                
                for artist in artists:
                    try:
                        artist_id = str(artist.ratingKey)
                        artist_name = getattr(artist, 'title', 'Unknown Artist')
                        thumb_url = getattr(artist, 'thumb', None)
                        
                        # Get genres if available
                        genres = []
                        if hasattr(artist, 'genres'):
                            try:
                                genres = [g.tag for g in artist.genres]
                            except:
                                pass
                        genres_json = ','.join(genres) if genres else None
                        
                        # Get summary/biography if available
                        summary = getattr(artist, 'summary', None)
                        
                        # Use INSERT OR REPLACE for conflict resolution
                        cursor.execute("""
                            INSERT OR REPLACE INTO artists 
                            (plex_artist_id, name, thumb_url, genres, summary, server_source, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM artists WHERE plex_artist_id = ?), datetime('now')), datetime('now'))
                        """, (artist_id, artist_name, thumb_url, genres_json, summary, server_source, artist_id))
                        
                        count += 1
                    except Exception as e:
                        logger.warning(f"Failed to insert artist {getattr(artist, 'title', 'Unknown')}: {e}")
                        continue
                
                logger.info(f"Bulk inserted/updated {count} artists")
                return count
                
        except Exception as e:
            logger.error(f"Error in bulk_insert_artists: {e}")
            return 0
    
    def bulk_insert_albums(self, albums: List[Any], artist_id: str, server_source: str = "plex") -> int:
        """
        Bulk insert or update albums for an artist.
        
        Args:
            albums: List of album objects
            artist_id: Parent artist ID
            server_source: Source server type
        
        Returns:
            Number of albums inserted/updated
        """
        if not albums:
            return 0
        
        try:
            with self._transaction():
                cursor = self.conn.cursor()
                count = 0
                
                for album in albums:
                    try:
                        album_id = str(album.ratingKey)
                        album_title = getattr(album, 'title', 'Unknown Album')
                        year = getattr(album, 'year', None)
                        thumb_url = getattr(album, 'thumb', None)
                        
                        # Get genres if available
                        genres = []
                        if hasattr(album, 'genres'):
                            try:
                                genres = [g.tag for g in album.genres]
                            except:
                                pass
                        genres_json = ','.join(genres) if genres else None
                        
                        # Track count and duration
                        track_count = getattr(album, 'leafCount', None)
                        
                        cursor.execute("""
                            INSERT OR REPLACE INTO albums
                            (plex_album_id, artist_id, title, year, thumb_url, genres, track_count, server_source, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM albums WHERE plex_album_id = ?), datetime('now')), datetime('now'))
                        """, (album_id, artist_id, album_title, year, thumb_url, genres_json, track_count, server_source, album_id))
                        
                        count += 1
                    except Exception as e:
                        logger.warning(f"Failed to insert album {getattr(album, 'title', 'Unknown')}: {e}")
                        continue
                
                logger.debug(f"Bulk inserted/updated {count} albums for artist {artist_id}")
                return count
                
        except Exception as e:
            logger.error(f"Error in bulk_insert_albums: {e}")
            return 0
    
    def bulk_insert_tracks(self, tracks: List[Any], album_id: str, artist_id: str, server_source: str = "plex") -> int:
        """
        Bulk insert or update tracks for an album.
        
        Args:
            tracks: List of track objects
            album_id: Parent album ID
            artist_id: Parent artist ID
            server_source: Source server type
        
        Returns:
            Number of tracks inserted/updated
        """
        if not tracks:
            return 0
        
        try:
            with self._transaction():
                cursor = self.conn.cursor()
                count = 0
                
                for track in tracks:
                    try:
                        track_id = str(track.ratingKey)
                        track_title = getattr(track, 'title', 'Unknown Track')
                        track_number = getattr(track, 'trackNumber', None)
                        duration = getattr(track, 'duration', None)
                        
                        # Get file path if available
                        file_path = None
                        if hasattr(track, 'media') and track.media:
                            try:
                                file_path = track.media[0].parts[0].file
                            except:
                                pass
                        
                        # Get bitrate if available
                        bitrate = None
                        if hasattr(track, 'media') and track.media:
                            try:
                                bitrate = track.media[0].bitrate
                            except:
                                pass
                        
                        cursor.execute("""
                            INSERT OR REPLACE INTO tracks
                            (plex_track_id, album_id, artist_id, title, track_number, duration, file_path, bitrate, server_source, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM tracks WHERE plex_track_id = ?), datetime('now')), datetime('now'))
                        """, (track_id, album_id, artist_id, track_title, track_number, duration, file_path, bitrate, server_source, track_id))
                        
                        count += 1
                    except Exception as e:
                        logger.warning(f"Failed to insert track {getattr(track, 'title', 'Unknown')}: {e}")
                        continue
                
                logger.debug(f"Bulk inserted/updated {count} tracks for album {album_id}")
                return count
                
        except Exception as e:
            logger.error(f"Error in bulk_insert_tracks: {e}")
            return 0
    
    def bulk_update_artist_content(self, artist: Any, albums: List[Any], server_source: str = "plex") -> tuple[int, int, int]:
        """
        Bulk update an artist with all their albums and tracks in one transaction.
        
        Args:
            artist: Artist object
            albums: List of album objects (with tracks accessible via album.tracks())
            server_source: Source server type
        
        Returns:
            Tuple of (artists_count, albums_count, tracks_count)
        """
        try:
            artist_id = str(artist.ratingKey)
            
            # Insert artist
            artists_count = self.bulk_insert_artists([artist], server_source)
            
            albums_count = 0
            tracks_count = 0
            
            # Insert albums and their tracks
            for album in albums:
                album_id = str(album.ratingKey)
                
                # Insert album
                albums_count += self.bulk_insert_albums([album], artist_id, server_source)
                
                # Get and insert tracks for this album
                try:
                    tracks = list(album.tracks())
                    tracks_count += self.bulk_insert_tracks(tracks, album_id, artist_id, server_source)
                except Exception as e:
                    logger.warning(f"Error getting tracks for album {getattr(album, 'title', 'Unknown')}: {e}")
            
            logger.info(f"Bulk updated artist {getattr(artist, 'title', 'Unknown')}: "
                       f"{albums_count} albums, {tracks_count} tracks")
            
            return (artists_count, albums_count, tracks_count)
            
        except Exception as e:
            logger.error(f"Error in bulk_update_artist_content: {e}")
            return (0, 0, 0)
