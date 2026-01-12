from typing import Protocol, List, Optional, Dict, Any
from core.matching_engine.soul_sync_track import SoulSyncTrack

class Provider(Protocol):
    """
    Strict Contract that all future providers (Python or Rust) must adhere to.
    """

    def search_tracks(self, query: str) -> List[SoulSyncTrack]:
        """
        Search for tracks based on a query string.

        Args:
            query: The search query.

        Returns:
            A list of SoulSyncTrack objects matching the query.
        """
        ...

    def get_track_by_id(self, item_id: str) -> Optional[SoulSyncTrack]:
        """
        Retrieve a specific track by its ID.

        Args:
            item_id: The unique identifier of the track.

        Returns:
            The SoulSyncTrack object if found, else None.
        """
        ...

    def get_artist_details(self, artist_id: str) -> Dict[str, Any]:
        """
        Retrieve details about an artist.

        Args:
            artist_id: The unique identifier of the artist.

        Returns:
            A dictionary containing artist details.
        """
        ...
