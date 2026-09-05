from unittest.mock import patch

from core.db.echo_sync_track import EchosyncTrack
from plugins.EchoSync.musicbrainz.client import MusicBrainzClient


def test_primary_artist_query_fallback():
    client = MusicBrainzClient()

    # Track with multi-artist credit separated by comma
    input_track = EchosyncTrack(
        raw_title="Energy",
        artist_name="Disclosure, Mick Jenkins",
        album_title="Energy",
        duration=290000,
    )

    searched_queries = []

    def mock_search_query(query, limit=5):
        searched_queries.append((query, limit))
        # Primary artist query should succeed
        q_low = query.lower()
        if 'artist:"disclosure"' in q_low and 'recording:"energy"' in q_low:
            return [
                {
                    "recording_id": "rec-123",
                    "title": "Energy",
                    "artist_name": "Disclosure",
                    "album_title": "Energy",
                    "score": 100,
                }
            ]
        return []

    mock_track = EchosyncTrack(
        raw_title="Energy",
        artist_name="Disclosure",
        album_title="Energy",
        duration=290000,
        musicbrainz_id="rec-123",
    )

    with (
        patch.object(client, "_search_metadata_query", side_effect=mock_search_query),
        patch.object(client, "get_track", return_value=mock_track),
    ):
        res = client.search_metadata(input_track)
        assert res is not None
        assert res.artist_name == "Disclosure"
        # Verify that primary artist query was executed
        assert any('artist:"disclosure"' in q[0].lower() for q in searched_queries)


def test_unquoted_artist_tokens_and_collaborative_scoring():
    client = MusicBrainzClient()

    # Input track has comma-separated artist credit
    input_track = EchosyncTrack(
        raw_title="New Vibe Who Dis",
        artist_name="Madison Mars, Feldz",
        album_title="",
        duration=180000,
    )

    searched_queries = []

    def mock_search_query(query, limit=5):
        searched_queries.append((query, limit))
        # Simulate Attempt 3 (unquoted artist tokens) succeeding
        if "artist:(madison mars)" in query.lower():
            return [
                {
                    "recording_id": "rec-madison",
                    "title": "New Vibe Who Dis",
                    "artist_name": "Madison Mars feat. Feldz",
                    "score": 100,
                }
            ]
        return []

    mock_track = EchosyncTrack(
        raw_title="New Vibe Who Dis",
        artist_name="Madison Mars feat. Feldz",
        album_title="New Vibe Who Dis",
        duration=180000,
        musicbrainz_id="rec-madison",
    )

    with (
        patch.object(client, "_search_metadata_query", side_effect=mock_search_query),
        patch.object(client, "get_track", return_value=mock_track),
    ):
        res = client.search_metadata(input_track)
        assert res is not None
        assert res.musicbrainz_id == "rec-madison"
        # Verify Attempt 3 was executed
        assert any("artist:(madison mars)" in q[0].lower() for q in searched_queries)


def test_recording_only_query_expanded_limit():
    client = MusicBrainzClient()

    input_track = EchosyncTrack(
        raw_title="Strobe",
        artist_name="deadmau5",
        album_title="For Lack of a Better Name",
        duration=637000,
    )

    searched_queries = []

    def mock_search_query(query, limit=5):
        searched_queries.append((query, limit))
        if query == 'recording:"strobe"':
            return [
                {
                    "recording_id": "rec-strobe",
                    "title": "Strobe",
                    "artist_name": "deadmau5",
                    "score": 100,
                }
            ]
        return []

    mock_track = EchosyncTrack(
        raw_title="Strobe",
        artist_name="deadmau5",
        album_title="For Lack of a Better Name",
        duration=637000,
        musicbrainz_id="rec-strobe",
    )

    with (
        patch.object(client, "_search_metadata_query", side_effect=mock_search_query),
        patch.object(client, "get_track", return_value=mock_track),
    ):
        res = client.search_metadata(input_track)
        assert res is not None
        # Check that recording-only query was called with limit=15
        recording_queries = [
            q for q in searched_queries if q[0] == 'recording:"strobe"'
        ]
        assert len(recording_queries) > 0
        assert recording_queries[0][1] == 15
