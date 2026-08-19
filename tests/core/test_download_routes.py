"""Tests for Downloads API routes."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from web.routes.downloads import router, core_router


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    app.include_router(core_router)
    return TestClient(app)


def test_delete_queue_empty_request(client):
    """Empty DELETE /api/v1/core/downloads/queue should clear queue without 422 error."""
    mock_db = MagicMock()
    mock_session = MagicMock()
    mock_query = MagicMock()
    mock_session.query.return_value = mock_query
    mock_query.delete.return_value = 5
    mock_db.session_scope.return_value.__enter__.return_value = mock_session

    with patch('web.routes.downloads.get_working_database', return_value=mock_db):
        resp = client.delete("/api/v1/core/downloads/queue")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True
        assert data.get("count") == 5


def test_delete_queue_with_scope_or_status(client):
    """DELETE /api/v1/core/downloads/queue with query params should filter and clear."""
    mock_db = MagicMock()
    mock_session = MagicMock()
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_filter
    mock_filter.delete.return_value = 2
    mock_db.session_scope.return_value.__enter__.return_value = mock_session

    with patch('web.routes.downloads.get_working_database', return_value=mock_db):
        resp = client.delete("/api/v1/core/downloads/queue?scope=failed")
        assert resp.status_code == 200
        assert resp.json().get("count") == 2


def test_delete_single_download_item(client):
    """DELETE /api/v1/core/downloads/{download_id} should delete specific download."""
    mock_db = MagicMock()
    mock_session = MagicMock()
    mock_query = MagicMock()
    mock_download = MagicMock()
    mock_session.query.return_value = mock_query
    mock_query.filter.return_value.first.return_value = mock_download
    mock_db.session_scope.return_value.__enter__.return_value = mock_session

    with patch('web.routes.downloads.get_working_database', return_value=mock_db):
        resp = client.delete("/api/v1/core/downloads/42")
        assert resp.status_code == 200
        assert resp.json().get("success") is True
        mock_session.delete.assert_called_once_with(mock_download)
