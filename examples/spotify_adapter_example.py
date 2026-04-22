"""
Example: Spotify Provider Adapter

This demonstrates how Spotify would be migrated to the new data-centric architecture.

BEFORE (Current): SpotifyClient owns Track data
AFTER (New): SpotifyAdapter creates stubs through music_database
"""

from typing import List, Dict, Optional, Any
from core.models import Track, ProviderType
from database.music_database import MusicDatabase


# SpotifyAdapter class example (ProviderAdapter base class removed)
class SpotifyAdapter:
    """
    Spotify adapter using canonical Track model.
    
    Responsibilities:
    - Create Track stubs from Spotify playlist/library data
    - Enrich Tracks with Spotify metadata
    - Attach Spotify provider_refs
    - NO data ownership - all operations through music_database
    """
    
    def __init__(self, db: MusicDatabase):
        super().__init__(db, ProviderType.SPOTIFY)
        
        # Initialize Spotify API client (authentication, etc.)
        from plugins.spotify.client import SpotifyClient
        self._client = SpotifyClient()  # Existing client for API calls
    
    # ========================================================================
    # ADAPTER CONTRACT IMPLEMENTATION
    # ========================================================================
    
    def get_provides_fields(self) -> List[str]:
        """Spotify can provide these Track fields"""
        return [
            'title',
            'artists',
            'album',
            'duration_ms',
            'isrc',                      # Spotify has ISRC!
            'album_artist',
            'track_number',
            'disc_number',
            'release_year',
            'genres',                    # From artist data
        ]
    
    def get_consumes_fields(self) -> List[str]:
        """Spotify needs these fields to search"""
        return ['title', 'artists']  # Minimal requirements for search
    
    def requires_auth(self) -> bool:
        """Spotify requires OAuth authentication"""
        return True
    
    # ========================================================================
    # SPOTIFY-SPECIFIC OPERATIONS
    # ========================================================================
    
    def import_playlist(self, playlist_id: str) -> List[str]:
        """
        Import Spotify playlist as Track stubs.
        
        OLD WAY: Returned Spotify-specific objects
        NEW WAY: Creates Track stubs in database, returns track_ids
        
        Args:
            playlist_id: Spotify playlist ID
            
        Returns:
            List of track_ids created
        """
        # Get playlist from Spotify API
        spotify_tracks = self._client.get_playlist_tracks(playlist_id)
        
        track_ids = []
        for spotify_track in spotify_tracks:
            # Check if track already exists by Spotify ID
            existing = self.find_by_provider_id(spotify_track['id'])
            
            if existing:
                # Track exists - just return its ID
                track_ids.append(existing.track_id)
            else:
                # Create new Track stub with Spotify data
                track_id = self.create_stub(
                    provider_id=spotify_track['id'],
                    title=spotify_track['name'],
                    artists=[artist['name'] for artist in spotify_track['artists']],
                    album=spotify_track['album']['name'],
                    duration_ms=spotify_track['duration_ms'],
                    isrc=spotify_track.get('external_ids', {}).get('isrc'),
                    album_artist=spotify_track['album']['artists'][0]['name'],
                    track_number=spotify_track.get('track_number'),
                    disc_number=spotify_track.get('disc_number'),
                    release_year=int(spotify_track['album']['release_date'][:4]) if spotify_track['album'].get('release_date') else None,
                )
                track_ids.append(track_id)
        
        return track_ids
    
    def enrich_from_spotify(self, track_id: str) -> Track:
        """
        Enrich existing Track with Spotify metadata.
        
        Use case: Track was created from Soulseek, now we want Spotify data
        
        Args:
            track_id: UUID of track to enrich
            
        Returns:
            Updated Track
        """
        # Get current track
        track = self.db.get_track(track_id)
        if not track:
            raise ValueError(f"Track {track_id} not found")
        
        # Search Spotify using existing track data
        query = f"{track.title} {' '.join(track.artists)}"
        results = self._client.search(query, type='track', limit=5)
        
        if not results:
            return track  # No match found
        
        # Find best match (using new MatchService)
        from services.match_service import MatchService, MatchContext
        from core.matching_engine import EchosyncTrack
        service = MatchService()
        
        source = EchosyncTrack(
            title=track.title,
            artist=track.artists[0] if track.artists else "",
            album=track.album or "",
            duration_ms=int((track.duration or 0) * 1000),
        )
        
        candidates = [
            EchosyncTrack(
                title=result['name'],
                artist=result['artists'][0]['name'] if result['artists'] else "",
                album=result['album']['name'] if result.get('album') else "",
                duration_ms=result.get('duration_ms', 0),
            )
            for result in results
        ]
        
        best_match_obj = service.find_best_match(source, candidates, context=MatchContext.DOWNLOAD_SEARCH)
        
        if best_match_obj and best_match_obj.confidence_score >= 70:
            # Get the original result for Spotify data
            best_match = next((r for r in results if r['name'] == best_match_obj.candidate_track.title), results[0])
            
            # Enrich with Spotify data
            enriched = self.enrich_track(
                track_id=track_id,
                isrc=best_match.get('external_ids', {}).get('isrc'),
                duration_ms=best_match.get('duration_ms'),
                album_artist=best_match['album']['artists'][0]['name'],
                track_number=best_match.get('track_number'),
                disc_number=best_match.get('disc_number'),
                release_year=int(best_match['album']['release_date'][:4]) if best_match['album'].get('release_date') else None,
            )
            
            # Attach Spotify provider_ref
            self.attach_provider_ref(
                track_id=track_id,
                provider_id=best_match['id'],
                provider_url=best_match['external_urls']['spotify'],
                metadata={'confidence': best_score}
            )
            
            return enriched
        
        return track  # No confident match
    
    def search_tracks(self, query: str, limit: int = 20) -> List[str]:
        """
        Search Spotify and create Track stubs for results.
        
        Args:
            query: Search query
            limit: Max results
            
        Returns:
            List of track_ids
        """
        results = self._client.search(query, type='track', limit=limit)
        
        track_ids = []
        for spotify_track in results:
            # Check if already exists
            existing = self.find_by_provider_id(spotify_track['id'])
            
            if existing:
                track_ids.append(existing.track_id)
            else:
                # Create stub
                track_id = self.create_stub(
                    provider_id=spotify_track['id'],
                    title=spotify_track['name'],
                    artists=[a['name'] for a in spotify_track['artists']],
                    album=spotify_track['album']['name'],
                    duration_ms=spotify_track['duration_ms'],
                    isrc=spotify_track.get('external_ids', {}).get('isrc'),
                )
                track_ids.append(track_id)
        
        return track_ids


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

def example_usage():
    """Example workflows with the new architecture"""
    from database.music_database import MusicDatabase
    
    # Initialize
    db = MusicDatabase()
    spotify = SpotifyAdapter(db)
    
    # Example 1: Import Spotify playlist
    track_ids = spotify.import_playlist("spotify:playlist:37i9dQZF1DXcBWIGoYBM5M")
    print(f"Imported {len(track_ids)} tracks")
    
    # Example 2: Get track details
    for track_id in track_ids[:5]:
        track = db.get_track(track_id)
        print(f"{track.title} by {', '.join(track.artists)} (confidence: {track.confidence_score:.2f})")
        
        # Check if we have Spotify reference
        if track.has_provider_ref(ProviderType.SPOTIFY):
            spotify_ref = track.get_provider_ref(ProviderType.SPOTIFY)
            print(f"  Spotify ID: {spotify_ref.provider_id}")
    
    # Example 3: Enrich track that was created from another source
    soulseek_track_id = "uuid-from-soulseek"
    enriched = spotify.enrich_from_spotify(soulseek_track_id)
    print(f"Enriched: {enriched}")
    
    # Example 4: Find track by ISRC (works across ALL providers)
    track = spotify.find_by_isrc("USUM71703692")
    if track:
        print(f"Found track by ISRC: {track.title}")
        print(f"Available in providers: {list(track.provider_refs.keys())}")


# ============================================================================
# MIGRATION CHECKLIST FOR SPOTIFY
# ============================================================================
"""
[x] Create SpotifyAdapter inheriting from ProviderAdapter
[x] Declare provides_fields/consumes_fields
[x] Convert import_playlist() to create Track stubs
[x] Convert search() to create Track stubs
[x] Add enrich_from_spotify() for existing tracks
[ ] Update SpotifyClient to use SpotifyAdapter internally
[ ] Update all call sites to use track_ids instead of Spotify objects
[ ] Update tests to mock music_database
[ ] Remove any Spotify-specific data storage
[ ] Update documentation
"""
