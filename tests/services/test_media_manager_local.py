"""
Tests for MediaManagerService — services/media_manager.py
"""

import pytest

from services.media_manager import MediaManagerService

# ── Fixture ────────────────────────────────────────────────────────────────────


@pytest.fixture()
def media_manager(monkeypatch, mock_db):
    """
    Construct a MediaManagerService in isolation:
      - Patches get_database() so no real database file is needed.
      - Patches event_bus.subscribe so test runs don't accumulate real handlers.
    """
    monkeypatch.setattr("services.media_manager.get_database", lambda: mock_db)
    monkeypatch.setattr(
        "services.media_manager.event_bus.subscribe", lambda *args, **kwargs: None
    )
    return MediaManagerService()
