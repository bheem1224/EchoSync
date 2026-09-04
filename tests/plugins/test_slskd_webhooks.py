"""
Test Suite for Stage 3: Centralized Webhook Gateway, SLSKD Ingestion & Transfer Hygiene.

Verifies:
1. Webhook routing rejects unqualified bare aliases (e.g. 'slskd') with 404.
2. Webhook routing accepts fully qualified dot-namespaces ('EchoSync.slskd') and CRC32 integer IDs.
3. Webhook secret authentication (both header and query param) and constant-time checking.
4. CIDR subnet filtering (200 on allowed subnet, 403 on disallowed external IP).
5. DownloadFileComplete webhook dispatches DownloadQueue to VERIFYING and emits DOWNLOAD_FILE_READY.
6. Transfer memory eviction on DOWNLOAD_COMPLETED and DOWNLOAD_FAILED events.
7. Connection self-healing: SERVICE_DEGRADED triggers reconnect_server with backoff.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.database.models.working import DownloadQueue, DownloadStatus
from core.event_bus import event_bus
from core.plugins.sdk import compute_plugin_crc32, sdk
from web.routes.webhooks import router as webhooks_router


@pytest.fixture
def webhook_client():
    """Create FastAPI test client with webhooks router."""
    app = FastAPI()
    app.include_router(webhooks_router)
    return TestClient(app)


def test_webhook_unqualified_alias_rejected(webhook_client):
    """Verifies that unqualified bare names like /api/v1/webhooks/slskd/... return HTTP 404."""
    # Bare unqualified 'slskd'
    resp = webhook_client.post("/api/v1/webhooks/slskd/download_status", json={"event": "test"})
    assert resp.status_code == 404
    assert "bare unqualified names are not permitted" in resp.json().get("detail", "")

    # Bare unqualified 'spotify'
    resp2 = webhook_client.post("/api/v1/webhooks/spotify/webhook", json={})
    assert resp2.status_code == 404


def test_webhook_crc32_and_namespaced_resolution(webhook_client):
    """Verifies both CRC32 integer ID and fully qualified dot-namespace route to the same handler."""
    namespace = "EchoSync.slskd"
    crc32_id = compute_plugin_crc32(namespace)
    slug = "test_endpoint"

    # Register endpoint with known secret
    secret_key = "sk_test_secret_12345"
    sdk.webhooks.register_endpoint(
        slug=slug,
        secret=secret_key,
        allow_unauthenticated=False,
        namespace=namespace,
    )

    # 1. Access via fully qualified dot-namespace with header secret
    resp_ns = webhook_client.post(
        f"/api/v1/webhooks/{namespace}/{slug}",
        json={"test": "data"},
        headers={"X-EchoSync-Webhook-Secret": secret_key},
    )
    assert resp_ns.status_code == 200
    assert resp_ns.json()["plugin_id"] == crc32_id
    assert resp_ns.json()["status"] == "ok"

    # 2. Access via numeric CRC32 integer ID with query param secret
    resp_crc = webhook_client.post(
        f"/api/v1/webhooks/{crc32_id}/{slug}?secret={secret_key}",
        json={"test": "data"},
    )
    assert resp_crc.status_code == 200
    assert resp_crc.json()["plugin_id"] == crc32_id
    assert resp_crc.json()["status"] == "ok"


def test_webhook_secret_authentication(webhook_client):
    """Verifies 401 Unauthorized for missing or invalid secrets."""
    namespace = "EchoSync.auth_test"
    crc32_id = compute_plugin_crc32(namespace)
    slug = "auth_slug"
    secret = "sk_secure_pass_999"

    sdk.webhooks.register_endpoint(
        slug=slug,
        secret=secret,
        allow_unauthenticated=False,
        namespace=namespace,
    )

    # Missing secret
    resp_missing = webhook_client.post(f"/api/v1/webhooks/{namespace}/{slug}", json={})
    assert resp_missing.status_code == 401

    # Wrong secret
    resp_wrong = webhook_client.post(
        f"/api/v1/webhooks/{namespace}/{slug}",
        headers={"X-EchoSync-Webhook-Secret": "wrong_secret"},
        json={},
    )
    assert resp_wrong.status_code == 401

    # Correct secret in header
    resp_ok = webhook_client.post(
        f"/api/v1/webhooks/{namespace}/{slug}",
        headers={"X-EchoSync-Webhook-Secret": secret},
        json={},
    )
    assert resp_ok.status_code == 200


def test_webhook_cidr_filtering(webhook_client):
    """Verifies CIDR subnet filtering: 200 for allowed IP, 403 for disallowed IP."""
    namespace = "EchoSync.cidr_test"
    slug = "cidr_slug"

    # Register endpoint allowing only 192.168.1.0/24 and 10.0.0.5
    sdk.webhooks.register_endpoint(
        slug=slug,
        allow_unauthenticated=True,
        allowed_subnets=["192.168.1.0/24", "10.0.0.5"],
        namespace=namespace,
    )

    # Request from allowed subnet (via X-Forwarded-For)
    resp_allowed = webhook_client.post(
        f"/api/v1/webhooks/{namespace}/{slug}",
        headers={"X-Forwarded-For": "192.168.1.50"},
        json={},
    )
    assert resp_allowed.status_code == 200

    # Request from disallowed external IP
    resp_blocked = webhook_client.post(
        f"/api/v1/webhooks/{namespace}/{slug}",
        headers={"X-Forwarded-For": "203.0.113.195"},
        json={},
    )
    assert resp_blocked.status_code == 403
    assert "Forbidden: IP address not allowed" in resp_blocked.json().get("detail", "")


def test_slskd_webhook_dispatches_verifying_state(webhook_client, mock_work_db):
    """Verifies that DownloadFileComplete transitions DownloadQueue to VERIFYING and emits DOWNLOAD_FILE_READY."""
    import plugins.EchoSync.slskd.plugin as slskd_plugin
    from services.download_manager import DownloadManager

    # 1. Create a mock downloading task in working.db
    task_id = 42
    with mock_work_db.session_scope() as session:
        queue_item = DownloadQueue(
            id=task_id,
            active_candidate_id="soul_user|test_track.flac",
            plugin_id="EchoSync.slskd",
            status=DownloadStatus.DOWNLOADING.value,
            echo_sync_track={"title": "test_track.flac", "file_path": "test_track.flac"},
        )
        session.add(queue_item)
        session.commit()

    # Track EventBus events
    ready_events = []

    def on_ready(payload):
        ready_events.append(payload)

    event_bus.subscribe("DOWNLOAD_FILE_READY", on_ready)

    # Ensure registration secret for EchoSync.slskd
    ep = sdk.webhooks.get_endpoint("download_status", namespace="EchoSync.slskd")
    if not ep:
        ep = sdk.webhooks.register_endpoint("download_status", namespace="EchoSync.slskd")
    secret = ep.get("secret")

    # Send DownloadFileComplete webhook payload
    payload = {
        "event": "DownloadFileComplete",
        "task_id": task_id,
        "username": "soul_user",
        "filename": "test_track.flac",
        "local_path": "/path/to/downloaded/test_track.flac",
    }

    with patch("services.download_manager.get_working_database", return_value=mock_work_db):
        resp = webhook_client.post(
            f"/api/v1/webhooks/EchoSync.slskd/download_status?secret={secret}",
            json=payload,
        )
        assert resp.status_code == 200

    # Verify state transitioned to VERIFYING
    with mock_work_db.session_scope() as session:
        item = session.get(DownloadQueue, task_id)
        assert item is not None
        assert item.status == DownloadStatus.VERIFYING.value

    # Verify DOWNLOAD_FILE_READY event published
    assert len(ready_events) >= 1
    assert ready_events[0].get("task_id") == task_id


@pytest.mark.asyncio
async def test_slskd_transfer_cleanup():
    """Verifies that DOWNLOAD_COMPLETED and DOWNLOAD_FAILED evict transfers from daemon memory."""
    from plugins.EchoSync.slskd.plugin import _on_download_completed_or_failed

    mock_provider = MagicMock()
    mock_provider.delete_transfer = AsyncMock(return_value=True)

    with patch("plugins.EchoSync.slskd.plugin._get_slskd_provider", return_value=mock_provider):
        # Trigger completed event
        await _on_download_completed_or_failed({
            "event": "DOWNLOAD_COMPLETED",
            "username": "test_user_alpha",
            "transfer_id": "file_uuid_123",
        })
        mock_provider.delete_transfer.assert_awaited_with("test_user_alpha", "file_uuid_123")

        # Trigger failed event
        await _on_download_completed_or_failed({
            "event": "DOWNLOAD_FAILED",
            "username": "test_user_beta",
            "transfer_id": "file_uuid_456",
        })
        mock_provider.delete_transfer.assert_awaited_with("test_user_beta", "file_uuid_456")


@pytest.mark.asyncio
async def test_slskd_auto_reconnect_on_degraded():
    """Verifies that SERVICE_DEGRADED triggers reconnect_server on the provider."""
    from plugins.EchoSync.slskd.plugin import _on_service_degraded

    mock_provider = MagicMock()
    mock_provider.reconnect_server = AsyncMock(return_value=True)

    with patch("plugins.EchoSync.slskd.plugin._get_slskd_provider", return_value=mock_provider), \
         patch("asyncio.sleep", AsyncMock()):
        await _on_service_degraded({
            "event": "SERVICE_DEGRADED",
            "service": "EchoSync.slskd",
            "reason": "Soulseek state degraded: disconnected",
        })
        mock_provider.reconnect_server.assert_awaited_once()
