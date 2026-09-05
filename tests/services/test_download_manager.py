"""Tests for DownloadManager Stage 1 closed-loop ingestion engine and DownloadQueue state machine."""

from unittest.mock import patch

import pytest

from core.database.models.working import DownloadIntent, DownloadQueue, DownloadStatus
from core.database.repositories.download_repo import DownloadRepository
from core.db.echo_sync_track import EchosyncTrack
from core.event_bus import event_bus
from services.download_manager import DownloadManager


@pytest.fixture()
def dm(mock_db, mock_work_db):
    """Fixture providing a fresh DownloadManager bound to test databases."""
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
    mgr.repo = DownloadRepository()
    yield mgr
    DownloadManager._instance = None


def test_state_machine_happy_path(dm, mock_work_db):
    """Verifies QUEUED -> SEARCHING -> DOWNLOADING -> VERIFYING -> COMPLETED lifecycle."""
    completed_events = []

    def on_completed(payload):
        completed_events.append(payload)

    event_bus.subscribe("DOWNLOAD_COMPLETED", on_completed)

    try:
        # 1. QUEUED: Track enqueued
        track = EchosyncTrack(
            sync_id="sync_happy_1",
            raw_title="Happy Track",
            artist_name="Daft Punk",
            album_title="Discovery",
        )
        download_id = dm.queue_download(track, intent=DownloadIntent.MANUAL_OMNI)
        assert download_id > 0

        with mock_work_db.session_scope() as session:
            item = session.get(DownloadQueue, download_id)
            assert item is not None
            assert item.status == DownloadStatus.QUEUED.value
            assert item.intent == DownloadIntent.MANUAL_OMNI.value
            assert item.sync_id == "sync_happy_1"
            assert item.retry_count == 0

        # 2. QUEUED -> SEARCHING
        res_searching = dm.transition_to_searching(download_id)
        assert res_searching is True

        with mock_work_db.session_scope() as session:
            item = session.get(DownloadQueue, download_id)
            assert item.status == DownloadStatus.SEARCHING.value

        # 3. SEARCHING -> DOWNLOADING (Top candidate selected, remaining into stack)
        cand1 = {
            "id": "peer1|happy.flac",
            "filename": "happy.flac",
            "username": "peer1",
        }
        cand2 = {
            "id": "peer2|happy.flac",
            "filename": "happy.flac",
            "username": "peer2",
        }
        cand3 = {
            "id": "peer3|happy.flac",
            "filename": "happy.flac",
            "username": "peer3",
        }

        res_downloading = dm.transition_to_downloading(
            download_id=download_id,
            active_candidate_id=cand1["id"],
            candidate_stack=[cand2, cand3],
            plugin_id="peer1|happy.flac",
        )
        assert res_downloading is True

        with mock_work_db.session_scope() as session:
            item = session.get(DownloadQueue, download_id)
            assert item.status == DownloadStatus.DOWNLOADING.value
            assert item.active_candidate_id == "peer1|happy.flac"
            assert item.candidate_stack == [cand2, cand3]
            assert not item.is_exhausted()

        # 4. DOWNLOADING -> VERIFYING (Download completed on provider, awaits verification)
        res_verifying = dm.transition_to_verifying(
            download_id, file_path="/data/downloads/happy.flac"
        )
        assert res_verifying is True

        with mock_work_db.session_scope() as session:
            item = session.get(DownloadQueue, download_id)
            assert item.status == DownloadStatus.VERIFYING.value
            assert not item.is_exhausted()

        # 5. VERIFYING -> COMPLETED (Verification succeeds, emits event)
        res_completed = dm.handle_verification_success(
            download_id, file_path="/data/downloads/happy.flac"
        )
        assert res_completed is True

        with mock_work_db.session_scope() as session:
            item = session.get(DownloadQueue, download_id)
            assert item.status == DownloadStatus.COMPLETED.value

        # Verify event was emitted
        import time
        time.sleep(0.1)
        assert len(completed_events) >= 1
        ev = completed_events[-1]
        ev_download_id = ev.get("download_id") or (ev.get("data") or {}).get(
            "download_id"
        )
        assert ev_download_id == download_id

    finally:
        event_bus.unsubscribe("DOWNLOAD_COMPLETED", on_completed)


def test_candidate_rotation_on_verification_failure(dm, mock_work_db):
    """Verifies that a rejected candidate is blacklisted, status changes to RETRYING, and candidate 2 is selected."""
    with mock_work_db.session_scope() as session:
        item = DownloadQueue(
            sync_id="sync_fail_1",
            intent=DownloadIntent.PLAYLIST_SYNC.value,
            status=DownloadStatus.VERIFYING.value,
            active_candidate_id="cand_1",
            candidate_stack=[{"id": "cand_2"}, {"id": "cand_3"}],
            retry_count=0,
            blacklisted_candidates=[],
        )
        session.add(item)
        session.commit()
        download_id = item.id

    # Simulate downstream verification failure (e.g., mismatch edition / unlabelled remix)
    with patch.object(dm, "_dispatch_candidate") as mock_dispatch:
        res = dm.handle_verification_failure(download_id, reason="MISMATCH_EDITION")
        assert res is True

    with mock_work_db.session_scope() as session:
        refreshed = session.get(DownloadQueue, download_id)
        assert refreshed.status == DownloadStatus.RETRYING.value
        assert refreshed.active_candidate_id == "cand_2"
        assert refreshed.retry_count == 1
        assert refreshed.candidate_stack == [{"id": "cand_3"}]
        assert len(refreshed.blacklisted_candidates) == 1
        assert refreshed.blacklisted_candidates[0] == {
            "candidate_id": "cand_1",
            "reason": "MISMATCH_EDITION",
        }
        assert not refreshed.is_exhausted()


def test_candidate_stack_exhaustion_marks_failed(dm, mock_work_db):
    """Verifies that failing 3 candidates terminates the task in FAILED with error_reason = 'CANDIDATES_EXHAUSTED'."""
    with mock_work_db.session_scope() as session:
        item = DownloadQueue(
            sync_id="sync_exhaust_1",
            intent=DownloadIntent.SUGGESTION_BACKFILL.value,
            status=DownloadStatus.VERIFYING.value,
            active_candidate_id="cand_1",
            candidate_stack=[{"id": "cand_2"}, {"id": "cand_3"}],
            retry_count=0,
            blacklisted_candidates=[],
        )
        session.add(item)
        session.commit()
        download_id = item.id

    with patch.object(dm, "_dispatch_candidate"):
        # Fail candidate 1 -> Rotate to candidate 2
        res1 = dm.handle_verification_failure(download_id, reason="CORRUPT_AUDIO")
        assert res1 is True

        with mock_work_db.session_scope() as session:
            i1 = session.get(DownloadQueue, download_id)
            assert i1.status == DownloadStatus.RETRYING.value
            assert i1.active_candidate_id == "cand_2"
            assert i1.retry_count == 1
            assert not i1.is_exhausted()

        # Fail candidate 2 -> Rotate to candidate 3
        res2 = dm.handle_verification_failure(download_id, reason="MISMATCH_EDITION")
        assert res2 is True

        with mock_work_db.session_scope() as session:
            i2 = session.get(DownloadQueue, download_id)
            assert i2.status == DownloadStatus.RETRYING.value
            assert i2.active_candidate_id == "cand_3"
            assert i2.retry_count == 2
            assert not i2.is_exhausted()

        # Fail candidate 3 -> Stack exhausted -> FAILED
        res3 = dm.handle_verification_failure(download_id, reason="UNAVAILABLE")
        assert res3 is False

        with mock_work_db.session_scope() as session:
            i3 = session.get(DownloadQueue, download_id)
            assert i3.status == DownloadStatus.FAILED.value
            assert i3.error_reason == "CANDIDATES_EXHAUSTED"
            assert i3.is_exhausted() is True
            assert len(i3.blacklisted_candidates) == 3
            assert i3.blacklisted_candidates[0]["candidate_id"] == "cand_1"
            assert i3.blacklisted_candidates[1]["candidate_id"] == "cand_2"
            assert i3.blacklisted_candidates[2]["candidate_id"] == "cand_3"
