"""Wave 3 unit tests: Download state machine, candidate rotation, repo/API filters, and slskd sync EventBus wrappers."""

from __future__ import annotations

import asyncio
import inspect
import threading
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.database.models.working import DownloadQueue, DownloadStatus
from core.database.repositories.download_repo import DownloadRepository
from core.event_bus import event_bus
from services.download_manager import DownloadManager
from web.routes.downloads import core_router, router


@pytest.fixture()
def dm(mock_db, mock_work_db):
    """Isolated DownloadManager bound to tmp_path test databases."""
    DownloadManager._instance = None
    with (
        patch("services.download_manager.get_database", return_value=mock_db),
        patch(
            "services.download_manager.get_working_database", return_value=mock_work_db
        ),
    ):
        mgr = DownloadManager.get_instance()
    mgr.db = mock_db
    mgr.work_db = mock_work_db
    mgr.repo = DownloadRepository(work_db=mock_work_db)
    yield mgr
    DownloadManager._instance = None


def test_download_status_unified_members_and_aliases():
    expected_canonical = {
        "QUEUED",
        "SEARCHING",
        "DOWNLOADING",
        "VERIFYING",
        "RETRYING",
        "COMPLETED",
        "FAILED",
        "CANCELLED",
        "PENDING_BLOCKED",
    }
    assert {s.value for s in DownloadStatus} == expected_canonical

    # Backward-compatible enum aliases
    assert DownloadStatus.COMPLETE is DownloadStatus.COMPLETED
    assert DownloadStatus.VERIFIED is DownloadStatus.COMPLETED
    assert DownloadStatus.CANCELED is DownloadStatus.CANCELLED
    assert DownloadStatus.IN_PROGRESS is DownloadStatus.DOWNLOADING

    # Case-insensitive equality
    assert DownloadStatus.VERIFYING == "verifying"
    assert DownloadStatus.PENDING_BLOCKED == "pending_blocked"
    assert DownloadStatus.CANCELLED == "cancelled"


def test_rotate_candidate_blacklists_on_column_and_respects_max_retries():
    item = DownloadQueue(
        sync_id="sync-rot-1",
        status=DownloadStatus.DOWNLOADING.value,
        active_candidate_id="peer1|song.flac",
        plugin_id="peer1|song.flac",
        echo_sync_track={"title": "Song", "artist_name": "Artist"},
        retry_count=0,
    )

    # Retry 1: RETRYING, active_candidate_id cleared, echo_sync_track untouched
    assert item.rotate_candidate(failed_candidate_id="peer1|song.flac", max_retries=3) is True
    assert item.status == DownloadStatus.RETRYING.value
    assert item.retry_count == 1
    assert item.active_candidate_id is None
    assert item.plugin_id is None
    assert "blacklisted_candidates" not in (item.echo_sync_track or {})

    # Retry 2: RETRYING
    item.active_candidate_id = "peer2|song.flac"
    assert item.rotate_candidate("peer2|song.flac", max_retries=3) is True
    assert item.status == DownloadStatus.RETRYING.value
    assert item.retry_count == 2
    assert item.active_candidate_id is None

    # Retry 3 (>= max_retries): FAILED
    item.active_candidate_id = "peer3|song.flac"
    assert item.rotate_candidate("peer3|song.flac", max_retries=3) is False
    assert item.status == DownloadStatus.FAILED.value
    assert item.retry_count == 3
    assert item.active_candidate_id is None
    assert item.error_reason == "CANDIDATES_EXHAUSTED"
    assert "blacklisted_candidates" not in (item.echo_sync_track or {})

    blacklisted_ids = [b["candidate_id"] for b in item.blacklisted_candidates]
    assert blacklisted_ids == ["peer1|song.flac", "peer2|song.flac", "peer3|song.flac"]


@pytest.mark.asyncio
async def test_check_active_downloads_uses_rotate_candidate_and_stops_at_max_retries(
    dm, mock_work_db
):
    with mock_work_db.session_scope() as session:
        item = DownloadQueue(
            sync_id="sync-active-fail",
            status=DownloadStatus.DOWNLOADING.value,
            active_candidate_id="peer1|track.flac",
            plugin_id="peer1|track.flac",
            retry_count=0,
            echo_sync_track={"title": "Track", "artist_name": "Artist"},
        )
        session.add(item)
        session.flush()
        db_id = item.id

    mock_provider = MagicMock()
    mock_provider.name = "MockDownloader"
    mock_provider._async_get_download_status = AsyncMock(
        return_value={"status": "failed", "progress": 0}
    )
    mock_provider._async_cancel_download = AsyncMock(return_value=True)

    with (
        patch.object(dm, "_get_active_download_providers", return_value=[mock_provider]),
        patch.object(
            dm, "_execute_waterfall_search_and_download", new_callable=AsyncMock
        ) as mock_waterfall,
    ):
        # Attempt 1 -> RETRYING (retry_count = 1)
        await dm._check_active_downloads()
        await asyncio.sleep(0)
        assert mock_waterfall.call_count == 1

        with mock_work_db.session_scope() as session:
            ref = session.get(DownloadQueue, db_id)
            assert ref.status == DownloadStatus.RETRYING.value
            assert ref.retry_count == 1
            assert ref.active_candidate_id is None
            assert "blacklisted_candidates" not in (ref.echo_sync_track or {})
            assert ref.blacklisted_candidates[0]["candidate_id"] == "peer1|track.flac"

            # Simulate reaching 3rd failure on peer3
            ref.status = DownloadStatus.DOWNLOADING.value
            ref.active_candidate_id = "peer3|track.flac"
            ref.plugin_id = "peer3|track.flac"
            ref.retry_count = 2

        await dm._check_active_downloads()
        await asyncio.sleep(0)

        # Exhausted at retry_count == 3 -> FAILED and no new waterfall task scheduled
        assert mock_waterfall.call_count == 1
        with mock_work_db.session_scope() as session:
            exhausted = session.get(DownloadQueue, db_id)
            assert exhausted.status == DownloadStatus.FAILED.value
            assert exhausted.retry_count == 3
            assert exhausted.active_candidate_id is None
            assert "blacklisted_candidates" not in (exhausted.echo_sync_track or {})
            assert [b["candidate_id"] for b in exhausted.blacklisted_candidates] == [
                "peer1|track.flac",
                "peer3|track.flac",
            ]


def test_on_track_imported_cancels_verifying_retrying_and_uses_active_candidate_id(
    dm, mock_work_db
):
    isrc = "USWAVE300001"
    with mock_work_db.session_scope() as session:
        rows = [
            DownloadQueue(
                sync_id="s-queued",
                status=DownloadStatus.QUEUED.value,
                echo_sync_track={"title": "Wave", "artist_name": "Artist", "isrc": isrc},
            ),
            DownloadQueue(
                sync_id="s-searching",
                status=DownloadStatus.SEARCHING.value,
                echo_sync_track={"title": "Wave", "artist_name": "Artist", "isrc": isrc},
            ),
            DownloadQueue(
                sync_id="s-downloading",
                status=DownloadStatus.DOWNLOADING.value,
                active_candidate_id="peer_x|wave.flac",
                plugin_id="plugin_logical_name",
                echo_sync_track={"title": "Wave", "artist_name": "Artist", "isrc": isrc},
            ),
            DownloadQueue(
                sync_id="s-verifying",
                status=DownloadStatus.VERIFYING.value,
                active_candidate_id="peer_y|wave.flac",
                echo_sync_track={"title": "Wave", "artist_name": "Artist", "isrc": isrc},
            ),
            DownloadQueue(
                sync_id="s-retrying",
                status=DownloadStatus.RETRYING.value,
                echo_sync_track={"title": "Wave", "artist_name": "Artist", "isrc": isrc},
            ),
            DownloadQueue(
                sync_id="s-other",
                status=DownloadStatus.VERIFYING.value,
                echo_sync_track={
                    "title": "Other",
                    "artist_name": "Other Artist",
                    "isrc": "USOTHER99999",
                },
            ),
        ]
        session.add_all(rows)
        session.flush()
        row_ids = [r.id for r in rows]

    mock_provider = MagicMock()
    mock_provider.cancel_download = MagicMock(return_value=True)

    with patch.object(dm, "_get_active_download_providers", return_value=[mock_provider]):
        dm._on_track_imported(
            {"track": {"title": "Wave", "artist_name": "Artist", "isrc": isrc}}
        )

    mock_provider.cancel_download.assert_called_once_with("peer_x|wave.flac")

    with mock_work_db.session_scope() as session:
        for deleted_id in row_ids[:-1]:
            assert session.get(DownloadQueue, deleted_id) is None
        survivor = session.get(DownloadQueue, row_ids[-1])
        assert survivor is not None
        assert survivor.status == DownloadStatus.VERIFYING.value


def test_on_track_imported_batch_pagination_does_not_skip_rows(dm, mock_work_db):
    isrc = "USBATCH00065"
    statuses = [
        DownloadStatus.QUEUED.value,
        DownloadStatus.VERIFYING.value,
        DownloadStatus.RETRYING.value,
    ]
    with mock_work_db.session_scope() as session:
        matching = [
            DownloadQueue(
                sync_id=f"batch-{i}",
                status=statuses[i % len(statuses)],
                echo_sync_track={
                    "title": "Batch Song",
                    "artist_name": "Batch Artist",
                    "isrc": isrc,
                },
            )
            for i in range(65)
        ]
        keep = [
            DownloadQueue(
                sync_id="keep-1",
                status=DownloadStatus.VERIFYING.value,
                echo_sync_track={
                    "title": "Keep Song",
                    "artist_name": "Keep Artist",
                    "isrc": "USKEEP000001",
                },
            ),
            DownloadQueue(
                sync_id="keep-2",
                status=DownloadStatus.RETRYING.value,
                echo_sync_track={
                    "title": "Keep Song 2",
                    "artist_name": "Keep Artist",
                    "isrc": "USKEEP000002",
                },
            ),
        ]
        session.add_all(matching + keep)
        session.flush()
        keep_ids = [k.id for k in keep]

    dm._on_track_imported(
        {
            "track": {
                "title": "Batch Song",
                "artist_name": "Batch Artist",
                "isrc": isrc,
            }
        }
    )

    with mock_work_db.session_scope() as session:
        remaining = session.query(DownloadQueue).order_by(DownloadQueue.id.asc()).all()
        assert [r.id for r in remaining] == keep_ids


def test_download_repo_and_routes_include_verifying_and_retrying(mock_work_db):
    repo = DownloadRepository(work_db=mock_work_db)
    with mock_work_db.session_scope() as session:
        for idx, st in enumerate(
            [
                DownloadStatus.QUEUED,
                DownloadStatus.SEARCHING,
                DownloadStatus.DOWNLOADING,
                DownloadStatus.VERIFYING,
                DownloadStatus.RETRYING,
                DownloadStatus.PENDING_BLOCKED,
                DownloadStatus.COMPLETED,
                DownloadStatus.FAILED,
                DownloadStatus.CANCELLED,
            ]
        ):
            session.add(
                DownloadQueue(
                    sync_id=f"st-{idx}",
                    status=st.value,
                    echo_sync_track={"title": f"Track {st.value}", "artist_name": "Artist"},
                )
            )

    active_repo_items = repo.get_active_downloads()
    assert {item.status for item in active_repo_items} == {
        DownloadStatus.SEARCHING.value,
        DownloadStatus.DOWNLOADING.value,
        DownloadStatus.VERIFYING.value,
        DownloadStatus.RETRYING.value,
    }

    actionable_items = repo.get_actionable_queue()
    assert {item.status for item in actionable_items} == {
        DownloadStatus.QUEUED.value,
        DownloadStatus.RETRYING.value,
    }

    app = FastAPI()
    app.include_router(router)
    app.include_router(core_router)
    client = TestClient(app)

    with patch("web.routes.downloads.get_working_database", return_value=mock_work_db):
        resp_active = client.get("/api/v1/core/downloads/active")
        assert resp_active.status_code == 200
        active_statuses = {item["status"] for item in resp_active.json()["items"]}
        assert active_statuses == {
            "QUEUED",
            "SEARCHING",
            "DOWNLOADING",
            "VERIFYING",
            "RETRYING",
            "PENDING_BLOCKED",
        }

        resp_verifying = client.get("/api/v1/core/downloads/queue?status=verifying")
        assert resp_verifying.status_code == 200
        assert [i["status"] for i in resp_verifying.json()["items"]] == ["VERIFYING"]

        resp_retrying = client.get("/api/v1/core/downloads/queue?status=retrying")
        assert resp_retrying.status_code == 200
        assert [i["status"] for i in resp_retrying.json()["items"]] == ["RETRYING"]

        resp_history = client.get("/api/v1/core/downloads/history")
        assert resp_history.status_code == 200
        assert {i["status"] for i in resp_history.json()["items"]} == {
            "COMPLETED",
            "FAILED",
            "CANCELLED",
        }

        resp_clear_active = client.delete("/api/v1/core/downloads/queue?scope=active")
        assert resp_clear_active.status_code == 200
        assert resp_clear_active.json()["count"] == 6

        resp_after = client.get("/api/v1/core/downloads/queue")
        assert resp_after.status_code == 200
        assert {i["status"] for i in resp_after.json()["items"]} == {
            "COMPLETED",
            "FAILED",
            "CANCELLED",
        }


def test_slskd_event_bus_subscribers_are_sync_and_thread_safe():
    import plugins.EchoSync.slskd.plugin as slskd_plugin

    with patch.object(
        slskd_plugin.sdk.webhooks,
        "register_endpoint",
        return_value={"url": "http://localhost/webhook", "secret": "test-secret"},
    ):
        slskd_plugin.initialize_plugin()

    # Every subscribed handler for slskd events must be synchronous (never a bare coroutine function)
    for ev_name in ("DOWNLOAD_COMPLETED", "DOWNLOAD_FAILED", "SERVICE_DEGRADED"):
        handlers = event_bus._subscribers.get(ev_name, [])
        assert handlers, f"Expected subscriber registered for {ev_name}"
        for h in handlers:
            assert not inspect.iscoroutinefunction(h)

    # Reconnect synchronization must use a thread-safe lock, never a module-level asyncio.Lock
    assert isinstance(slskd_plugin._RECONNECT_LOCK, type(threading.Lock()))

    mock_provider = MagicMock()
    mock_provider.delete_transfer = AsyncMock(return_value=True)
    mock_provider.reconnect_server = AsyncMock(return_value=True)

    slskd_plugin._RECONNECT_ATTEMPTS = 0
    with (
        patch.object(slskd_plugin, "_get_slskd_provider", return_value=mock_provider),
        patch.object(slskd_plugin.asyncio, "sleep", AsyncMock()),
    ):
        event_bus.publish(
            {
                "event": "DOWNLOAD_COMPLETED",
                "username": "peer_sync_1",
                "transfer_id": "tx_1",
            }
        )
        event_bus.publish(
            {
                "event": "DOWNLOAD_FAILED",
                "username": "peer_sync_2",
                "transfer_id": "tx_2",
            }
        )
        event_bus.publish(
            {
                "event": "SERVICE_DEGRADED",
                "service": "EchoSync.slskd",
            }
        )
        event_bus.publish(
            {
                "event": "SERVICE_DEGRADED",
                "service": "EchoSync.slskd",
            }
        )

        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            if (
                mock_provider.delete_transfer.await_count >= 2
                and mock_provider.reconnect_server.await_count >= 1
            ):
                break
            time.sleep(0.05)

        mock_provider.delete_transfer.assert_any_await("peer_sync_1", "tx_1")
        mock_provider.delete_transfer.assert_any_await("peer_sync_2", "tx_2")
        assert mock_provider.reconnect_server.await_count >= 1
