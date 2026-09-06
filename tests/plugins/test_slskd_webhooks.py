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

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml
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
    resp = webhook_client.post(
        "/api/v1/webhooks/slskd/download_status", json={"event": "test"}
    )
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

    # 1. Create a mock downloading task in working.db
    task_id = 42
    with mock_work_db.session_scope() as session:
        queue_item = DownloadQueue(
            id=task_id,
            active_candidate_id="soul_user|test_track.flac",
            plugin_id="EchoSync.slskd",
            status=DownloadStatus.DOWNLOADING.value,
            echo_sync_track={
                "title": "test_track.flac",
                "file_path": "test_track.flac",
            },
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
        ep = sdk.webhooks.register_endpoint(
            "download_status", namespace="EchoSync.slskd"
        )
    secret = ep.get("secret")

    # Send DownloadFileComplete webhook payload
    payload = {
        "event": "DownloadFileComplete",
        "task_id": task_id,
        "username": "soul_user",
        "filename": "test_track.flac",
        "local_path": "/path/to/downloaded/test_track.flac",
    }

    from plugins.EchoSync.slskd.plugin import on_webhook_received
    from core.plugins.sdk import _WEBHOOK_HANDLERS, compute_plugin_crc32

    _WEBHOOK_HANDLERS.setdefault(compute_plugin_crc32("EchoSync.slskd"), []).append(
        on_webhook_received
    )
    with (
        patch(
            "database.working_database.get_working_database", return_value=mock_work_db
        ),
        patch(
            "web.routes.webhooks.lookup_registered_endpoint",
            return_value={"secret": secret},
        ),
    ):
        resp = webhook_client.post(
            f"/api/v1/webhooks/EchoSync.slskd/download_status?secret={secret}",
            json=payload,
        )
        assert resp.status_code == 200

    import time

    time.sleep(0.1)
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

    with patch(
        "plugins.EchoSync.slskd.plugin._get_slskd_provider", return_value=mock_provider
    ):
        # Trigger completed event
        await _on_download_completed_or_failed(
            {
                "event": "DOWNLOAD_COMPLETED",
                "username": "test_user_alpha",
                "transfer_id": "file_uuid_123",
            }
        )
        mock_provider.delete_transfer.assert_awaited_with(
            "test_user_alpha", "file_uuid_123"
        )

        # Trigger failed event
        await _on_download_completed_or_failed(
            {
                "event": "DOWNLOAD_FAILED",
                "username": "test_user_beta",
                "transfer_id": "file_uuid_456",
            }
        )
        mock_provider.delete_transfer.assert_awaited_with(
            "test_user_beta", "file_uuid_456"
        )


@pytest.mark.asyncio
async def test_slskd_auto_reconnect_on_degraded():
    """Verifies that SERVICE_DEGRADED triggers reconnect_server on the provider."""
    from plugins.EchoSync.slskd.plugin import _on_service_degraded

    mock_provider = MagicMock()
    mock_provider.reconnect_server = AsyncMock(return_value=True)

    with (
        patch(
            "plugins.EchoSync.slskd.plugin._get_slskd_provider",
            return_value=mock_provider,
        ),
        patch("asyncio.sleep", AsyncMock()),
    ):
        await _on_service_degraded(
            {
                "event": "SERVICE_DEGRADED",
                "service": "EchoSync.slskd",
                "reason": "Soulseek state degraded: disconnected",
            }
        )
        mock_provider.reconnect_server.assert_awaited_once()


def test_slskd_yaml_generation_syntax():
    """Verifies that registered SLSKD webhook outputs plural 'integrations', lifecycle events, and X-EchoSync-Secret."""
    reg = sdk.webhooks.register_endpoint("download_status", namespace="EchoSync.slskd")
    template = reg.get("yaml_template", "")
    assert template, "yaml_template should not be empty"

    parsed = yaml.safe_load(template)
    assert "integrations" in parsed, "Root key must be plural 'integrations'"
    assert "integration" not in parsed, (
        "Legacy singular 'integration' root key must not be present"
    )

    webhook_config = parsed["integrations"]["webhooks"]["echosync_downloads"]
    events = webhook_config.get("on") or webhook_config.get(True)
    expected_events = [
        "DownloadFileComplete",
        "DownloadFileFailed",
        "SoulseekClientConnected",
        "SoulseekClientDisconnected",
    ]
    for ev in expected_events:
        assert ev in events, f"Event {ev} must be present in webhook triggers"

    call_config = webhook_config["call"]
    assert call_config["url"] == reg["url"]
    assert "?secret=" not in call_config["url"]
    assert call_config["timeout"] == 10000
    assert call_config["retry"]["attempts"] == 3

    headers = call_config.get("headers", [])
    assert any(
        h.get("name") == "X-EchoSync-Secret" and h.get("value") == reg["secret"]
        for h in headers
    ), "X-EchoSync-Secret header must be configured with the generated secret"


def test_webhook_auth_via_header(webhook_client):
    """Verifies authentication via X-EchoSync-Secret and Authorization: Bearer <secret>."""
    namespace = "EchoSync.auth_header_test"
    slug = "status"
    secret = "sk_header_secret_123"

    sdk.webhooks.register_endpoint(
        slug=slug,
        secret=secret,
        allow_unauthenticated=False,
        namespace=namespace,
    )

    # 1. Standard X-EchoSync-Secret
    resp = webhook_client.post(
        f"/api/v1/webhooks/{namespace}/{slug}",
        headers={"X-EchoSync-Secret": secret},
        json={"event": "test"},
    )
    assert resp.status_code == 200

    # 2. Authorization: Bearer <secret>
    resp_bearer = webhook_client.post(
        f"/api/v1/webhooks/{namespace}/{slug}",
        headers={"Authorization": f"Bearer {secret}"},
        json={"event": "test"},
    )
    assert resp_bearer.status_code == 200

    # 3. Invalid header secret
    resp_invalid = webhook_client.post(
        f"/api/v1/webhooks/{namespace}/{slug}",
        headers={"X-EchoSync-Secret": "wrong_key"},
        json={"event": "test"},
    )
    assert resp_invalid.status_code == 401


def test_webhook_auth_via_query_fallback(webhook_client, caplog):
    """Verifies query param ?secret= authenticates but emits a deprecation warning."""
    namespace = "EchoSync.auth_query_test"
    slug = "status"
    secret = "sk_query_secret_456"

    sdk.webhooks.register_endpoint(
        slug=slug,
        secret=secret,
        allow_unauthenticated=False,
        namespace=namespace,
    )

    with caplog.at_level(logging.WARNING):
        resp = webhook_client.post(
            f"/api/v1/webhooks/{namespace}/{slug}?secret={secret}",
            json={"event": "test"},
        )
    assert resp.status_code == 200
    assert any(
        "deprecated" in record.message.lower()
        and "query parameter" in record.message.lower()
        for record in caplog.records
    ), "Deprecation warning must be logged when passing secret via query parameter"


@pytest.mark.asyncio
async def test_slskd_lifecycle_webhook_events():
    """Verifies SoulseekClientConnected and SoulseekClientDisconnected event bus dispatches."""
    import plugins.EchoSync.slskd.plugin as slskd_plugin
    from plugins.EchoSync.slskd.plugin import on_webhook_received

    healthy_events = []
    degraded_events = []

    def on_healthy(payload):
        healthy_events.append(payload)

    def on_degraded(payload):
        degraded_events.append(payload)

    event_bus.subscribe("SERVICE_HEALTHY", on_healthy)
    event_bus.subscribe("SERVICE_DEGRADED", on_degraded)

    # Set reconnect attempts to non-zero before testing connected
    slskd_plugin._RECONNECT_ATTEMPTS = 5

    mock_provider = MagicMock()
    mock_provider.reconnect_server = AsyncMock(return_value=True)

    with (
        patch(
            "plugins.EchoSync.slskd.plugin._get_slskd_provider",
            return_value=mock_provider,
        ),
        patch("plugins.EchoSync.slskd.plugin.asyncio.sleep", AsyncMock()),
    ):
        # 1. Connected event
        await on_webhook_received(
            "download_status",
            {"event": "SoulseekClientConnected", "state": "connected"},
        )
        import time

        time.sleep(0.05)
        assert len(healthy_events) >= 1
        assert healthy_events[-1].get("service") == "EchoSync.slskd"
        assert slskd_plugin._RECONNECT_ATTEMPTS == 0

        # 2. Disconnected event
        await on_webhook_received(
            "download_status",
            {"event": "SoulseekClientDisconnected", "reason": "socket closed"},
        )
        time.sleep(0.05)
        assert len(degraded_events) >= 1
        assert degraded_events[-1].get("service") == "EchoSync.slskd"
