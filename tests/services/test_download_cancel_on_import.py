"""
Tests for DownloadManager._on_track_imported queue cancellation.
— services/download_manager.py —

When the TRACK_IMPORTED event fires (a file has been confirmed in the local
library), the Download Manager must silently cancel any active or queued
downloads whose ISRC matches the imported track.  This prevents duplicate
files appearing on disk and avoids redundant provider searches.

Coverage:
  • ISRC match in 'queued' state       → status becomes 'cancelled'
  • ISRC match in 'searching' state    → status becomes 'cancelled'
  • ISRC match in 'downloading' state  → status becomes 'cancelled'
  • ISRC mismatch                      → download left untouched
  • Cancellation reason recorded       → echo_sync_track dict gets the key
  • Already-cancelled download         → not in active_states, stays as-is
  • Empty / malformed payload          → method returns silently, no exception
  • Multiple matching downloads        → all are cancelled
"""

import pytest
from unittest.mock import patch

from time_utils import utc_now
from database.working_database import Download
from core.matching_engine.echo_sync_track import EchosyncTrack
from services.download_manager import DownloadManager


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture()
def manager(mock_db, mock_work_db):
    """
    Yield a DownloadManager whose database references point at the test
    fixtures rather than any real on-disk databases.

    The singleton is reset before and after this fixture so tests are fully
    isolated from each other and from any other test module that may have
    already initialised a DownloadManager instance.
    """
    DownloadManager._instance = None

    with patch("services.download_manager.get_database", return_value=mock_db), \
         patch("services.download_manager.get_working_database",
               return_value=mock_work_db):
        mgr = DownloadManager.get_instance()

    # Guarantee correct db references even if the singleton was already live.
    mgr.db = mock_db
    mgr.work_db = mock_work_db

    yield mgr

    DownloadManager._instance = None   # tear-down: clean slate for next test


# ── Helper ─────────────────────────────────────────────────────────────────────

def _insert_download(work_db, isrc: str, status: str = "queued") -> int:
    """Insert a single Download row and return its primary-key id.

    The title and artist_name are derived from the ISRC so that two downloads
    with different ISRCs also have different names.  This prevents the
    artist+title name-match fallback in _on_track_imported from accidentally
    cancelling an unrelated download in tests that assert non-cancellation.
    """
    track_json = {
        "title": f"Track {isrc}",
        "artist_name": f"Artist {isrc}",
        "isrc": isrc,
    }
    with work_db.session_scope() as session:
        dl = Download(
            sync_id=f"ss:isrc:{isrc}",
            echo_sync_track=track_json,
            status=status,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add(dl)
        session.flush()
        return dl.id


def _make_imported_payload(isrc: str) -> dict:
    """Build the dict that the TRACK_IMPORTED event carries.

    Uses the same ISRC-derived title/artist as _insert_download so that the
    ISRC path AND the name-match fallback both resolve consistently.
    """
    return {
        "track": {
            "title": f"Track {isrc}",
            "artist_name": f"Artist {isrc}",
            "isrc": isrc,
        }
    }


# ── Core cancellation logic ────────────────────────────────────────────────────

class TestTrackImportedCancelsQueue:

    def test_queued_download_is_cancelled_on_isrc_match(self, manager, mock_work_db):
        """
        A download in 'queued' state whose ISRC matches the imported track
        must have its status changed to 'cancelled'.
        """
        isrc = "USRC12345678"
        dl_id = _insert_download(mock_work_db, isrc, status="queued")

        manager._on_track_imported(_make_imported_payload(isrc))

        with mock_work_db.session_scope() as session:
            dl = session.get(Download, dl_id)
            assert dl.status == "cancelled"

    def test_searching_download_is_cancelled_on_isrc_match(self, manager, mock_work_db):
        """
        A download already promoted to 'searching' (provider query in-flight)
        must also be cancelled when the track lands in the library.
        """
        isrc = "GBRC12345670"
        dl_id = _insert_download(mock_work_db, isrc, status="searching")

        manager._on_track_imported(_make_imported_payload(isrc))

        with mock_work_db.session_scope() as session:
            dl = session.get(Download, dl_id)
            assert dl.status == "cancelled"

    def test_downloading_download_is_cancelled_on_isrc_match(self, manager, mock_work_db):
        """
        A download in 'downloading' state (file transfer has begun) must be
        cancelled when TRACK_IMPORTED confirms the file is already present.
        """
        isrc = "FRUM12345671"
        dl_id = _insert_download(mock_work_db, isrc, status="downloading")

        manager._on_track_imported(_make_imported_payload(isrc))

        with mock_work_db.session_scope() as session:
            dl = session.get(Download, dl_id)
            assert dl.status == "cancelled"

    def test_non_matching_isrc_leaves_download_untouched(self, manager, mock_work_db):
        """
        A queued download whose ISRC differs from the imported track's ISRC
        must not have its status modified.
        """
        dl_id = _insert_download(mock_work_db, isrc="USRC99999999", status="queued")

        manager._on_track_imported(_make_imported_payload("USRC00000000"))

        with mock_work_db.session_scope() as session:
            dl = session.get(Download, dl_id)
            assert dl.status == "queued"    # fully unchanged

    def test_cancellation_reason_written_to_track_json(self, manager, mock_work_db):
        """
        After cancellation, the download's echo_sync_track dict must contain
        a 'cancellation_reason' key so operators can audit why it was dropped.
        """
        isrc = "DECP12345672"
        dl_id = _insert_download(mock_work_db, isrc, status="queued")

        manager._on_track_imported(_make_imported_payload(isrc))

        with mock_work_db.session_scope() as session:
            dl = session.get(Download, dl_id)
            assert dl.status == "cancelled"
            assert isinstance(dl.echo_sync_track, dict)
            assert "cancellation_reason" in dl.echo_sync_track
            assert len(dl.echo_sync_track["cancellation_reason"]) > 0

    def test_already_cancelled_download_is_not_reprocessed(self, manager, mock_work_db):
        """
        A download whose status is already 'cancelled' is excluded from the
        active_states query and must not be further modified.
        """
        isrc = "USRC77777777"
        dl_id = _insert_download(mock_work_db, isrc, status="cancelled")

        # A second import of the same track must not change anything.
        manager._on_track_imported(_make_imported_payload(isrc))

        with mock_work_db.session_scope() as session:
            dl = session.get(Download, dl_id)
            assert dl.status == "cancelled"    # already there — unchanged


# ── Multiple simultaneous matching downloads ───────────────────────────────────

class TestBatchCancellation:

    def test_all_active_matching_downloads_are_cancelled(self, manager, mock_work_db):
        """
        When several downloads (in different active states) share the same ISRC,
        every one of them must be cancelled in a single event handler call.
        """
        isrc = "USRC55555555"
        ids = [
            _insert_download(mock_work_db, isrc, status="queued"),
            _insert_download(mock_work_db, isrc, status="searching"),
            _insert_download(mock_work_db, isrc, status="downloading"),
        ]

        manager._on_track_imported(_make_imported_payload(isrc))

        with mock_work_db.session_scope() as session:
            for dl_id in ids:
                dl = session.get(Download, dl_id)
                assert dl.status == "cancelled", (
                    f"Download {dl_id} was expected to be cancelled but is '{dl.status}'"
                )

    def test_unrelated_downloads_survive_batch_cancellation(self, manager, mock_work_db):
        """
        When multiple downloads with different ISRCs are present, only the
        matching ones must be cancelled; the rest must survive untouched.
        """
        target_isrc = "USRC11111111"
        other_isrc  = "USRC22222222"

        target_id = _insert_download(mock_work_db, target_isrc, status="queued")
        other_id  = _insert_download(mock_work_db, other_isrc,  status="queued")

        manager._on_track_imported(_make_imported_payload(target_isrc))

        with mock_work_db.session_scope() as session:
            target_dl = session.get(Download, target_id)
            other_dl  = session.get(Download, other_id)

            assert target_dl.status == "cancelled"
            assert other_dl.status  == "queued"     # unaffected


# ── Graceful handling of malformed / empty payloads ───────────────────────────

class TestMalformedPayloadHandling:

    def test_empty_payload_does_not_raise(self, manager):
        """An event payload with no 'track' key must be silently swallowed."""
        try:
            manager._on_track_imported({})
        except Exception as exc:
            pytest.fail(f"_on_track_imported raised unexpectedly on empty payload: {exc}")

    def test_none_track_data_does_not_raise(self, manager):
        """Explicit None value for 'track' must be silently swallowed."""
        try:
            manager._on_track_imported({"track": None})
        except Exception as exc:
            pytest.fail(f"_on_track_imported raised unexpectedly on None track: {exc}")

    def test_missing_isrc_in_imported_track_does_not_cancel_by_isrc(
        self, manager, mock_work_db
    ):
        """
        If the imported track carries no ISRC, the ISRC-match path must be
        skipped.  A queued download with an ISRC must not be auto-cancelled
        solely because a track without ISRC was imported.
        """
        isrc = "USRC33333333"
        dl_id = _insert_download(mock_work_db, isrc, status="queued")

        # Fire an import event with no ISRC — only artist+title available,
        # and the names don't match the queued download's names either.
        manager._on_track_imported({
            "track": {
                "title": "Completely Different Song",
                "artist_name": "Different Artist",
                # no 'isrc' key
            }
        })

        with mock_work_db.session_scope() as session:
            dl = session.get(Download, dl_id)
            # Not cancelled: ISRC mismatch path; name-match also fails.
            assert dl.status == "queued"
