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
            acc = Account(id=1, name="Test Account", service="local")
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
