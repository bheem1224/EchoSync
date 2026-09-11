"""Unit tests for AcoustIDProvider (plugins/EchoSync/acoustid/client.py)."""

from plugins.EchoSync.acoustid.client import AcoustIDProvider


class DummyHTTP:
    def __init__(self, response_data, status_code=200):
        self.response_data = response_data
        self.status_code = status_code
        self.last_data = None
        self.last_url = None

    def post(self, url, data):
        self.last_url = url
        self.last_data = data

        class DummyResp:
            def __init__(self, data, code):
                self._data = data
                self.status_code = code

            def json(self):
                return self._data

        return DummyResp(self.response_data, self.status_code)


def test_acoustid_lookup_payload_meta_parameter():
    """Verify AcoustID provider sends required meta parameters, client, int duration, and fingerprint."""
    provider = AcoustIDProvider()
    dummy_http = DummyHTTP({"status": "ok", "results": []})
    provider.http = dummy_http
    provider.config = {"api_key": "test_api_key_123"}

    res = provider.resolve_fingerprint_details("AQAAtest_fingerprint", 200.6)

    assert dummy_http.last_url == "https://api.acoustid.org/v2/lookup"
    assert dummy_http.last_data["client"] == "test_api_key_123"
    assert dummy_http.last_data["meta"] == "recordings recordingids releases releasegroups tracks compress"
    assert dummy_http.last_data["duration"] == 201
    assert isinstance(dummy_http.last_data["duration"], int)
    assert dummy_http.last_data["fingerprint"] == "AQAAtest_fingerprint"
    assert res["match_status"] == "UNRESOLVED"


def test_acoustid_response_recordings_ingestion():
    """Verify AcoustID response parsing unpacks recordings with id, title, artist, duration, and score."""
    sample_response = {
        "status": "ok",
        "results": [
            {
                "id": "bc645d59-137f-401e-a9a4-61ff6bad28cf",
                "score": 0.97402424,
                "recordings": [
                    {
                        "id": "d2555d82-e889-4fa2-9388-7521d897f26d",
                        "title": "There's Nothing Holdin' Me Back",
                        "duration": 200,
                        "artists": [{"id": "b7ffd2af-418f-4be2-bdd1-22f8b48613da", "name": "Shawn Mendes"}],
                        "releasegroups": [{"id": "rg-1", "title": "Illuminate"}],
                    }
                ],
                "recordingids": ["d2555d82-e889-4fa2-9388-7521d897f26d"],
            },
            {
                "id": "alt-cluster-2",
                "score": 0.85,
                "recordings": [
                    {
                        "id": "alt-rec-id-2",
                        "title": "Alternate Track",
                        "duration": 205.5,
                        "artist": "Fallback Artist",
                    }
                ],
            },
        ],
    }

    provider = AcoustIDProvider()
    dummy_http = DummyHTTP(sample_response)
    provider.http = dummy_http
    provider.config = {"api_key": "test_api_key"}

    res = provider.resolve_fingerprint_details("AQAA_valid_fp", 201)

    assert res["acoustid_id"] == "bc645d59-137f-401e-a9a4-61ff6bad28cf"
    assert res["score"] == 0.97402424
    assert res["match_status"] == "MATCHED"

    # Both MBIDs should be present
    assert "d2555d82-e889-4fa2-9388-7521d897f26d" in res["mbids"]
    assert "alt-rec-id-2" in res["mbids"]

    # Verify recordings unpacking
    recordings = res["recordings"]
    assert len(recordings) == 2

    rec1 = recordings[0]
    assert rec1["id"] == "d2555d82-e889-4fa2-9388-7521d897f26d"
    assert rec1["title"] == "There's Nothing Holdin' Me Back"
    assert rec1["artist"] == "Shawn Mendes"
    assert rec1["duration"] == 200.0
    assert rec1["score"] == 0.97402424

    rec2 = recordings[1]
    assert rec2["id"] == "alt-rec-id-2"
    assert rec2["title"] == "Alternate Track"
    assert rec2["artist"] == "Fallback Artist"
    assert rec2["duration"] == 205.5
    assert rec2["score"] == 0.85


def test_acoustid_deep_title_and_artist_extraction_from_releasegroups():
    """Verify that when a recording omits top-level title and artists,
    metadata is deeply extracted from nested releasegroups.releases.mediums.tracks.
    """
    nested_response = {
        "status": "ok",
        "results": [
            {
                "id": "e00bfad7-nested-cluster",
                "score": 0.956,
                "recordings": [
                    {
                        "id": "d2555d82-deep-extraction",
                        "duration": 200.6,
                        # Intentionally omitting top-level "title" and "artists"
                        "releasegroups": [
                            {
                                "id": "rg-shawn-illuminate",
                                "title": "Illuminate",
                                "type": "Album",
                                "artists": [{"id": "art-shawn", "name": "Shawn Mendes"}],
                                "releases": [
                                    {
                                        "id": "rel-illuminate-deluxe",
                                        "mediums": [
                                            {
                                                "tracks": [
                                                    {
                                                        "id": "trk-1",
                                                        "title": "There's Nothing Holdin' Me Back",
                                                        "artists": [{"name": "Shawn Mendes"}],
                                                    }
                                                ]
                                            }
                                        ],
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        ],
    }

    provider = AcoustIDProvider()
    dummy_http = DummyHTTP(nested_response)
    provider.http = dummy_http
    provider.config = {"api_key": "test_key"}

    res = provider.resolve_fingerprint_details("AQAA_deep_fp", 201)

    recordings = res.get("recordings", [])
    assert len(recordings) == 1

    rec = recordings[0]
    assert rec["id"] == "d2555d82-deep-extraction"
    assert rec["title"] == "There's Nothing Holdin' Me Back"
    assert rec["artist"] == "Shawn Mendes"
    assert rec["duration"] == 200.6
    assert rec["score"] == 0.956
