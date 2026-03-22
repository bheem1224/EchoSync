import requests
import logging

logger = logging.getLogger("tidal_api")

class TidalAPI:
    BASE_URL = "https://openapi.tidal.com/v2"

    def __init__(self, access_token: str, country_code: str = "US"):
        self.access_token = access_token
        self.country_code = country_code
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def _get(self, endpoint: str, params: dict = None):
        url = f"{self.BASE_URL}{endpoint}"
        if params is None:
            params = {}
        params["countryCode"] = self.country_code
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Tidal API request failed: {e}")
            return None

    def get_user_playlists(self):
        """Fetch user playlists with pagination."""
        endpoint = "/my-collection/playlists"
        playlists = []
        params = {"limit": 50}
        has_more = True

        while has_more:
            data = self._get(endpoint, params)
            if not data or "items" not in data:
                has_more = False
                continue

            playlists.extend(data["items"])

            if "next" in data:
                params["cursor"] = data["next"]
                # Rate limiting is managed by the caller's RequestManager;
                # no manual sleep needed here.
            else:
                has_more = False

        return playlists

    def get_playlist_tracks(self, playlist_id: str):
        """Fetch tracks from a playlist, including artist and album metadata."""
        endpoint = f"/playlists/{playlist_id}/relationships/items"
        params = {
            "include": "items.artists,items.album",
            "limit": 100
        }
        tracks = []
        has_more = True

        while has_more:
            data = self._get(endpoint, params)
            if not data or "items" not in data:
                has_more = False
                continue

            # Parse included data
            included = {item["id"]: item for item in data.get("included", [])}

            for item in data["items"]:
                track = {
                    "title": item["title"],
                    "isrc": item.get("isrc"),
                    "artist_name": ", ".join(
                        included[rel["id"]]["name"] for rel in item["artists"]
                        if rel["id"] in included
                    ),
                    "album_name": included[item["album"]["id"]]["title"]
                    if "album" in item and item["album"]["id"] in included else None,
                    "duration_ms": item.get("duration", 0)
                }
                tracks.append(track)

            if "next" in data:
                params["cursor"] = data["next"]
                # Rate limiting is managed by the caller's RequestManager;
                # no manual sleep needed here.
            else:
                has_more = False

        return tracks