from unittest.mock import MagicMock, patch

from requests import Response

from core.request_manager import HttpError, RequestManager, RetryConfig
from plugins.EchoSync.musicbrainz.client import MusicBrainzClient


def test_request_manager_retry_after_handling():
    """Verify RequestManager respects Retry-After numeric header."""
    rm = RequestManager(
        "test_provider",
        retry=RetryConfig(max_retries=3, base_backoff=0.1, max_backoff=5.0),
    )
    resp = Response()
    resp.status_code = 503
    resp.headers["Retry-After"] = "0.05"

    with patch("time.sleep") as mock_sleep:
        rm._backoff_sleep(1, resp=resp)
        mock_sleep.assert_called_once_with(0.05)


def test_musicbrainz_fetch_artist_tracks_graceful_503(monkeypatch):
    """Verify MusicBrainz client gracefully handles HTTP 503 during artist track fetch."""
    client = MusicBrainzClient()

    # Simulate 503 on the first call
    def mock_get(*args, **kwargs):
        resp = Response()
        resp.status_code = 503
        raise HttpError(
            "HTTP 503 for https://musicbrainz.org/ws/2/recording",
            status=503,
            response=resp,
        )

    monkeypatch.setattr(client.http, "get", mock_get)

    tracks = client._fetch_artist_track_dicts("rihanna")
    assert tracks == []


def test_musicbrainz_fetch_artist_tracks_partial_on_subsequent_503(monkeypatch):
    """Verify MusicBrainz client preserves tracks fetched prior to receiving a 503 on subsequent pages."""
    client = MusicBrainzClient()

    calls = 0

    def mock_get(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {
                "recordings": [
                    {
                        "id": "mbid-1",
                        "title": "Umbrella",
                        "artist-credit": [{"name": "Rihanna"}],
                        "releases": [
                            {"title": "Good Girl Gone Bad", "date": "2007-05-30"}
                        ],
                    }
                ]
            }
            return resp
        else:
            resp = Response()
            resp.status_code = 503
            raise HttpError(
                "HTTP 503 for https://musicbrainz.org/ws/2/recording",
                status=503,
                response=resp,
            )

    monkeypatch.setattr(client.http, "get", mock_get)

    tracks = client._fetch_artist_track_dicts("rihanna")
    assert len(tracks) == 1
    assert tracks[0]["title"] == "Umbrella"
