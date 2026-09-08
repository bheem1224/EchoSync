import pytest
from fastapi.testclient import TestClient

from database.working_database import (
    Account,
    SuggestionStagingQueue,
    get_working_database,
)
from web.api_app import create_app


@pytest.fixture
def client():
    app = create_app(testing=True)
    with TestClient(app) as client:
        yield client


def test_get_suggestion_queue_empty(client):
    """Verify GET /api/v1/system/manager/queue/suggestions returns empty list when no items."""
    resp = client.get("/api/v1/system/manager/queue/suggestions")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("success") is True
    assert isinstance(data.get("suggestions"), list)


def test_get_suggestion_queue_serialization(client):
    """Verify GET /api/v1/system/manager/queue/suggestions successfully serializes items
    without raising AttributeError on music_db_track_id or user_id."""
    work_db = get_working_database()

    with work_db.session_scope() as session:
        # Ensure an account exists
        acc = session.query(Account).first()
        if not acc:
            acc = Account(id=1, plugin_id=1, remote_account_id="acc-1", username="Test Account")
            session.add(acc)
            session.flush()
        account_id = acc.id

        # Insert a suggestion with context data
        item1 = SuggestionStagingQueue(
            account_id=account_id,
            sync_id="sync-item-1",
            reason="HYGIENE_DUPLICATION",
            intent_type="HYGIENE_DUPLICATION",
            ui_label="Bohemian Rhapsody - Remaster 2011",
            context_data={
                "title": "Bohemian Rhapsody",
                "artist": "Queen",
                "album": "A Night at the Opera",
                "score": 0.98,
                "originator": "Consensus Engine",
                "action_needed": "DELETE_LOW_QUALITY",
                "track_id": 42,
            },
            status="pending",
        )

        # Insert a suggestion with minimal/None context data
        item2 = SuggestionStagingQueue(
            account_id=account_id,
            sync_id="sync-item-2",
            reason="playlist_gap",
            ui_label="Another One Bites the Dust",
            context_data=None,
            status="pending",
        )

        session.add(item1)
        session.add(item2)

    try:
        resp = client.get("/api/v1/system/manager/queue/suggestions")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True

        suggestions = data.get("suggestions", [])
        sync_ids = [s["sync_id"] for s in suggestions]
        assert "sync-item-1" in sync_ids
        assert "sync-item-2" in sync_ids

        # Verify item1 fields
        s1 = next(s for s in suggestions if s["sync_id"] == "sync-item-1")
        assert s1["title"] == "Bohemian Rhapsody - Remaster 2011"
        assert s1["artist"] == "Queen"
        assert s1["album"] == "A Night at the Opera"
        assert s1["score"] == 0.98
        assert s1["status"] == "pending"
        assert s1["track_id"] == 42
        assert s1["type"] == "HYGIENE_DUPLICATION"
        assert s1["account_id"] == account_id

        # Verify item2 fields with None context
        s2 = next(s for s in suggestions if s["sync_id"] == "sync-item-2")
        assert s2["title"] == "Another One Bites the Dust"
        assert s2["status"] == "pending"
        assert s2["track_id"] is None
        assert s2["account_id"] == account_id
    finally:
        with work_db.session_scope() as session:
            session.query(SuggestionStagingQueue).filter(
                SuggestionStagingQueue.sync_id.in_(["sync-item-1", "sync-item-2"])
            ).delete(synchronize_session=False)


def test_get_suggestion_queue_hydrates_duplicate_payload(client: TestClient):
    """Verify GET /api/v1/system/manager/queue/suggestions returns enriched winner/loser tracks,
    comparison reason, and formatted duplicate title."""
    work_db = get_working_database()

    with work_db.session_scope() as session:
        acc = session.query(Account).first()
        if not acc:
            acc = Account(id=1, plugin_id=1, remote_account_id="acc-1", username="Test Account")
            session.add(acc)
            session.flush()
        account_id = acc.id

        dup_payload = {
            "type": "Duplicate Resolution",
            "originator": "System",
            "event": "system_duplicate",
            "subtype": "acoustic_duplicate",
            "confidence_score": 100.0,
            "reason": "Acoustic duplicate detected",
            "winner_track": {
                "id": 101,
                "title": "Hotel California",
                "artist": "Eagles",
                "album": "Hotel California",
                "format": "flac",
                "bitrate": 1411000,
                "sample_rate": 44100,
                "file_path": "/music/Eagles/Hotel California.flac",
                "duration": 390000,
            },
            "loser_track": {
                "id": 102,
                "title": "Hotel California",
                "artist": "Eagles",
                "album": "Hotel California (Remaster)",
                "format": "mp3",
                "bitrate": 320000,
                "sample_rate": 44100,
                "file_path": "/music/Eagles/Hotel California.mp3",
                "duration": 390500,
            },
        }

        item = SuggestionStagingQueue(
            account_id=account_id,
            sync_id="sync-dup-test-1",
            reason="HYGIENE_DUPLICATION",
            intent_type="HYGIENE_DUPLICATION",
            ui_label="Review needed for system_duplicate",
            context_data=dup_payload,
            status="pending",
        )
        session.add(item)

    try:
        resp = client.get("/api/v1/system/manager/queue/suggestions")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True

        suggestions = data.get("suggestions", [])
        dup_sugg = next(
            (s for s in suggestions if s["sync_id"] == "sync-dup-test-1"), None
        )
        assert dup_sugg is not None

        # Verify title formatted to "{Artist} - {Title} (Duplicate)"
        assert dup_sugg["title"] == "Eagles - Hotel California (Duplicate)"
        assert dup_sugg["comparison_reason"] == "Acoustic Match (100%)"

        # Verify winner_track hydrated
        winner = dup_sugg["winner_track"]
        assert winner is not None
        assert winner["id"] == 101
        assert winner["title"] == "Hotel California"
        assert winner["artist"] == "Eagles"
        assert winner["format"] == "flac"
        assert winner["bitrate"] == 1411000
        assert winner["file_path"] == "/music/Eagles/Hotel California.flac"

        # Verify loser_track hydrated
        loser = dup_sugg["loser_track"]
        assert loser is not None
        assert loser["id"] == 102
        assert loser["format"] == "mp3"
        assert loser["bitrate"] == 320000
        assert loser["file_path"] == "/music/Eagles/Hotel California.mp3"

        # Test swap endpoint
        swap_resp = client.post(
            "/api/v1/system/manager/suggestions/sync-dup-test-1/swap"
        )
        assert swap_resp.status_code == 200
        swap_data = swap_resp.json()
        assert swap_data.get("success") is True
        assert swap_data["winner_track"]["id"] == 102
        assert swap_data["loser_track"]["id"] == 101

    finally:
        with work_db.session_scope() as session:
            session.query(SuggestionStagingQueue).filter(
                SuggestionStagingQueue.sync_id == "sync-dup-test-1"
            ).delete(synchronize_session=False)

