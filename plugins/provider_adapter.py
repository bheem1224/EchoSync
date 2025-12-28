"""
Provider Adapter Base Class

This module defines the base adapter interface that ALL providers must implement.
Adapters enforce the architectural rule: Providers NEVER own data.

All operations go through music_database via the Track model.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from core.models import Track, ProviderType
from database.music_database import MusicDatabase


class ProviderAdapter(ABC):
    """
    Base adapter for all providers.
    
    Architectural Rules Enforced:
    1. Providers NEVER store Track data locally
    2. All Track operations go through music_database
    3. Providers only create stubs, enrich fields, or attach refs
    4. No direct database access - use provided methods
    
    Workflow:
    1. create_stub() - Create minimal Track with provider_ref
    2. enrich_track() - Add fields to existing Track
    3. update_status() - Update download_status or confidence_score
    """
    
    def __init__(self, db: MusicDatabase, provider_type: ProviderType):
        """
        Initialize adapter with database connection.
        
        Args:
            db: MusicDatabase instance (single source of truth)
            provider_type: ProviderType enum for this adapter
        """
        self.db = db
        self.provider_type = provider_type
    
    # ========================================================================
    # CORE ADAPTER METHODS (All providers must implement)
    # ========================================================================
    
    @abstractmethod
    def get_provides_fields(self) -> List[str]:
        """
        Declare which Track fields this provider can populate.
        
        Returns:
            List of field names from TRACK_FIELDS
            
        Example:
            return ['title', 'artists', 'album', 'duration_ms', 'isrc']
        """
        pass
    
    @abstractmethod
    def get_consumes_fields(self) -> List[str]:
        """
        Declare which Track fields this provider requires to operate.
        
        Returns:
            List of field names from TRACK_FIELDS
            
        Example:
            return ['title', 'artists']  # Need these to search
        """
        pass
    
    @abstractmethod
    def requires_auth(self) -> bool:
        """Whether this provider requires authentication"""
        pass
    
    # ========================================================================
    # TRACK OPERATIONS (Standardized across all providers)
    # ========================================================================
    
    def create_stub(self, provider_id: str, **initial_fields) -> str:
        """
        Create a new Track stub in the database.
        
        This is the ONLY way providers create tracks.
        Automatically attaches provider_ref.
        
        Args:
            provider_id: Provider's native ID for this track
            **initial_fields: Initial Track fields (from provides_fields)
            
        Returns:
            track_id: UUID of created track
            
        Example:
            track_id = self.create_stub(
                provider_id="spotify:track:abc123",
                title="Song Name",
                artists=["Artist Name"],
                duration_ms=180000
            )
        """
        # Create Track instance
        track = Track(**initial_fields)
        
        # Attach provider reference
        track.add_provider_ref(
            provider=self.provider_type,
            provider_id=provider_id
        )
        
        # Persist to database
        track_id = self.db.create_track(track)
        
        return track_id
    
    def enrich_track(self, track_id: str, **fields) -> Track:
        """
        Enrich an existing Track with additional fields.
        
        This is the ONLY way providers add data to tracks.
        Only updates empty fields (never overwrites).
        
        Args:
            track_id: UUID of track to enrich
            **fields: Fields to add (from provides_fields)
            
        Returns:
            Updated Track instance
            
        Example:
            track = self.enrich_track(
                track_id=track_id,
                musicbrainz_recording_id="mbid-123",
                acoustid="aid-456"
            )
        """
        # Get current track
        track = self.db.get_track(track_id)
        if not track:
            raise ValueError(f"Track {track_id} not found")
        
        # Enrich (only fills empty fields)
        track.enrich(**fields)
        
        # Persist changes
        self.db.update_track(track)
        
        return track
    
    def attach_provider_ref(self, track_id: str, provider_id: str, 
                           provider_url: Optional[str] = None,
                           metadata: Optional[Dict[str, Any]] = None) -> Track:
        """
        Attach or update provider reference to an existing Track.
        
        Args:
            track_id: UUID of track
            provider_id: Provider's native ID
            provider_url: Optional direct URL
            metadata: Optional provider-specific metadata
            
        Returns:
            Updated Track instance
        """
        track = self.db.get_track(track_id)
        if not track:
            raise ValueError(f"Track {track_id} not found")
        
        track.add_provider_ref(
            provider=self.provider_type,
            provider_id=provider_id,
            provider_url=provider_url,
            metadata=metadata
        )
        
        self.db.update_track(track)
        
        return track
    
    def update_download_status(self, track_id: str, status: str, 
                              file_path: Optional[str] = None,
                              file_format: Optional[str] = None,
                              bitrate: Optional[int] = None) -> Track:
        """
        Update download-related fields for a Track.
        
        Args:
            track_id: UUID of track
            status: DownloadStatus value ("missing", "queued", "downloading", "complete", "verified")
            file_path: Local file path if downloaded
            file_format: File format (e.g., "flac", "mp3")
            bitrate: Bitrate in bps
            
        Returns:
            Updated Track instance
        """
        track = self.db.get_track(track_id)
        if not track:
            raise ValueError(f"Track {track_id} not found")
        
        # Update download fields
        from core.models import DownloadStatus
        track.download_status = DownloadStatus(status)
        
        if file_path:
            track.file_path = file_path
        if file_format:
            track.file_format = file_format
        if bitrate:
            track.bitrate = bitrate
        
        # Recalculate confidence
        track._calculate_confidence()
        
        self.db.update_track(track)
        
        return track
    
    # ========================================================================
    # SEARCH & MATCHING HELPERS
    # ========================================================================
    
    def find_by_provider_id(self, provider_id: str) -> Optional[Track]:
        """Find Track by provider ID"""
        return self.db.find_track_by_provider_ref(self.provider_type.value, provider_id)
    
    def find_by_isrc(self, isrc: str) -> Optional[Track]:
        """Find Track by ISRC"""
        return self.db.find_track_by_isrc(isrc)
    
    def find_by_musicbrainz_id(self, mbid: str) -> Optional[Track]:
        """Find Track by MusicBrainz recording ID"""
        return self.db.find_track_by_musicbrainz_id(mbid)
    
    def fuzzy_match(self, title: str, artists: List[str], 
                   album: Optional[str] = None, 
                   threshold: float = 0.7) -> List[Track]:
        """
        Find tracks by fuzzy matching on metadata.
        
        Args:
            title: Track title
            artists: Artist names
            album: Optional album name
            threshold: Minimum confidence score (0.0-1.0)
            
        Returns:
            List of matching Tracks sorted by confidence
        """
        return self.db.fuzzy_match_tracks(
            title=title,
            artists=artists,
            album=album,
            threshold=threshold
        )
