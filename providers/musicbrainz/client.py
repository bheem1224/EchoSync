from typing import List, Optional, Dict, Any
from core.provider_base import ProviderBase
from core.enums import Capability
from core.request_manager import RateLimitConfig
from core.matching_engine.soul_sync_track import SoulSyncTrack
from core.tiered_logger import get_logger

logger = get_logger("provider.musicbrainz")

class MusicBrainzProvider(ProviderBase):
    name = "musicbrainz"
    service_type = "metadata"
    capabilities = [Capability.FETCH_METADATA]

    def __init__(self):
        super().__init__()
        # Enforce strict 1 req/sec rate limit
        self.http.rate = RateLimitConfig(requests_per_second=1.0)

        # Set User-Agent as per MusicBrainz policy
        self.http._session.headers.update({
            "User-Agent": "SoulSync/0.1.0 ( https://github.com/soulsync/soulsync )"
        })
        self.api_base = "https://musicbrainz.org/ws/2"

    def get_metadata(self, mbid: str) -> Optional[Dict[str, Any]]:
        """
        Fetch detailed metadata for a recording MBID.
        Includes: title, artist, album, date, IDs, cover art URL (if available via Cover Art Archive).
        """
        try:
            params = {
                'fmt': 'json',
                'inc': 'artists+releases+tags+isrcs+media'
            }
            response = self.http.get(f"{self.api_base}/recording/{mbid}", params=params)

            if response.status_code != 200:
                logger.error(f"MusicBrainz API error: {response.status_code}")
                return None

            data = response.json()

            # Base metadata
            metadata = {
                'title': data.get('title'),
                'recording_id': data.get('id'),  # TXXX: MusicBrainz Track Id
                'artist': '',
                'artist_id': '',  # TXXX: MusicBrainz Artist Id
                'album': '',
                'release_id': '',  # TXXX: MusicBrainz Release Id
                'date': '',
                'track_number': None,
                'disc_number': None,
                'cover_art_url': None,
                'isrc': None
            }

            # ISRCs
            if data.get('isrcs'):
                metadata['isrc'] = data['isrcs'][0]

            # Artist Credit
            if data.get('artist-credit'):
                parts = []
                for credit in data['artist-credit']:
                    if isinstance(credit, dict):
                        parts.append(credit.get('name', ''))
                        if credit.get('joinphrase'):
                            parts.append(credit.get('joinphrase', ''))
                metadata['artist'] = "".join(parts)

                # Use first artist ID
                if len(data['artist-credit']) > 0 and 'artist' in data['artist-credit'][0]:
                    metadata['artist_id'] = data['artist-credit'][0]['artist']['id']

            # Release Info (Album, Track, Disc)
            releases = data.get('releases', [])
            selected_release = None

            # Prioritize Official releases
            official_releases = [r for r in releases if r.get('status') == 'Official']
            if official_releases:
                selected_release = official_releases[0]
            elif releases:
                selected_release = releases[0]

            if selected_release:
                metadata['album'] = selected_release.get('title')
                metadata['release_id'] = selected_release.get('id')
                metadata['date'] = selected_release.get('date')  # YYYY-MM-DD

                # Extract Track & Disc Number
                # Loop through media to find the track associated with this recording
                for media in selected_release.get('media', []):
                    for track in media.get('tracks', []):
                        if track.get('id') == mbid or (track.get('recording') and track.get('recording').get('id') == mbid):
                            metadata['track_number'] = track.get('number')
                            metadata['disc_number'] = media.get('position')
                            break
                    if metadata['track_number']:
                        break

                # Fetch cover art if we have a release ID
                if metadata['release_id']:
                    metadata['cover_art_url'] = self._get_cover_art(metadata['release_id'])

            return metadata

        except Exception as e:
            logger.error(f"Failed to fetch metadata for {mbid}: {e}")
            return None

    def search_metadata(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for recordings by query.
        """
        try:
            params = {
                'fmt': 'json',
                'query': query,
                'limit': limit
            }
            response = self.http.get(f"{self.api_base}/recording", params=params)

            if response.status_code != 200:
                return []

            data = response.json()
            results = []

            for recording in data.get('recordings', []):
                # Basic info
                res = {
                    'title': recording.get('title'),
                    'mbid': recording.get('id'),
                    'score': recording.get('score'),
                    'artist': '',
                    'album': ''
                }

                if recording.get('artist-credit'):
                    parts = []
                    for credit in recording['artist-credit']:
                        if isinstance(credit, dict):
                            parts.append(credit.get('name', ''))
                    res['artist'] = " & ".join(parts)

                if recording.get('releases'):
                    res['album'] = recording['releases'][0].get('title')

                results.append(res)

            return results

        except Exception as e:
            logger.error(f"Failed to search metadata: {e}")
            return []

    def _get_cover_art(self, release_id: str) -> Optional[str]:
        """Fetch front cover URL from Cover Art Archive"""
        try:
            # Check CAA index first to avoid 404s/redirect loops if possible, or just HEAD
            # But simpler to just GET the image URL which CAA redirects to.
            # Note: Requests follows redirects by default.
            url = f"https://coverartarchive.org/release/{release_id}/front"

            # HEAD request to check existence and get final URL
            resp = self.http.request('HEAD', url, allow_redirects=True)
            if resp.status_code == 200:
                return resp.url
            return None
        except Exception:
            return None

    # Abstract methods
    def authenticate(self, **kwargs) -> bool: return True
    def search(self, query: str, type: str = "track", limit: int = 10) -> List[SoulSyncTrack]: return []
    def get_track(self, track_id: str) -> Optional[SoulSyncTrack]: return None
    def get_album(self, album_id: str) -> Optional[Dict[str, Any]]: return None
    def get_artist(self, artist_id: str) -> Optional[Dict[str, Any]]: return None
    def get_user_playlists(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]: return []
    def get_playlist_tracks(self, playlist_id: str) -> List[SoulSyncTrack]: return []
    def is_configured(self) -> bool: return True
    def get_logo_url(self) -> str: return "https://musicbrainz.org/static/images/entity/musicbrainz_logo.svg"
