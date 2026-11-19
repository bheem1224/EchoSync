"""Wave 3 unit tests for metadata_review, deletion lifecycle, state_listener plugin resolution, and bounded caches."""

from __future__ import annotations

import threading
import zlib
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from core.security.rbac import Principal, principal_scope
from core.suggestion_engine import consensus as consensus_mod
from core.suggestion_engine import deletion as deletion_mod
from core.suggestion_engine.deletion import (
    DELETE_MONTH_END,
    UPGRADE_WEEK_END,
    apply_lifecycle_actions_batch,
    process_lifecycle_actions,
)
from database import _canonicalize_path
from database.config_database import ConfigDatabase, close_config_database
from database.music_database import (
    Artist,
    Base,
    ExternalIdentifier,
    LocalMedia,
    MusicDatabase,
    Track,
    close_database,
    generate_nanoid,
)
from database.working_database import (
    Account,
    PlaybackHistory,
    ReviewTask,
    UserTrackState,
    WorkingBase,
    WorkingDatabase,
    close_working_database,
)
from services.playlist_sync import (
    ANALYSIS_JOBS,
    MATCH_TRACE_CACHE,
    BoundedTTLCache,
    cache_match_trace,
    clear_match_trace_cache,
    get_cached_match_trace,
)
from services.state_listener import StateListenerService
from time_utils import utc_now
from web.api_app import create_app
from web.routes import playlists as playlists_route
from web.routes.metadata_review import (
    ApproveReviewQueueRequest,
    _get_media_file_path,
    _serialize_task,
    approve_review_queue_item,
)


@pytest.fixture
def isolated_review_env(tmp_path, monkeypatch):
    """Set up isolated music/working DBs and storage dirs under tmp_path."""
    close_database()
    close_working_database()

    library_dir = tmp_path / "library"
    download_dir = tmp_path / "downloads"
    poor_dir = tmp_path / "poor_metadata"
    for d in (library_dir, download_dir, poor_dir):
        d.mkdir(parents=True, exist_ok=True)

    music_db = MusicDatabase(str(tmp_path / "music_wave3.db"))
    Base.metadata.create_all(music_db.engine)

    work_db = WorkingDatabase(str(tmp_path / "working_wave3.db"))
    WorkingBase.metadata.create_all(work_db.engine)

    def mock_config_get(key, default=None):
        if key in ("storage.library_dir", "library_dir"):
            return str(library_dir)
        if key in ("storage.download_dir", "download_dir"):
            return str(download_dir)
        if key == "storage.poor_metadata_dir":
            return str(poor_dir)
        if key == "library_preferences":
            return (str(library_dir), "{Artist}/{Album}/{Track} - {Title}.{ext}")
        if key == "file_organization_pattern":
            return "{Artist}/{Album}/{Track} - {Title}.{ext}"
        return default

    monkeypatch.setattr("core.settings.config_manager.get", mock_config_get)
    monkeypatch.setattr(
        "core.path_formatter.get_library_preferences",
        lambda: (str(library_dir), "{Artist}/{Album}/{Track} - {Title}.{ext}"),
    )
    monkeypatch.setattr("web.routes.metadata_review.get_database", lambda: music_db)
    monkeypatch.setattr("web.routes.metadata_review.get_working_database", lambda: work_db)
    monkeypatch.setattr("database.music_database.get_database", lambda *a, **kw: music_db)
    monkeypatch.setattr("database.working_database.get_working_database", lambda *a, **kw: work_db)

    class SyncJobQueue:
        def register_job(self, name, func, interval_seconds=None):
            self._func = func

        def execute_job_now(self, name):
            self._func()

        @contextmanager
        def db_write_lease(self, task_name="", timeout=30.0):
            yield

    import core.task_manager.task_queue as tq_mod

    monkeypatch.setattr(tq_mod, "job_queue", SyncJobQueue())

    try:
        yield {
            "tmp_path": tmp_path,
            "music_db": music_db,
            "work_db": work_db,
            "library_dir": library_dir,
            "download_dir": download_dir,
            "poor_dir": poor_dir,
        }
    finally:
        close_database()
        close_working_database()


def test_background_approval_tag_verification_failure_persists_failed_state(isolated_review_env, monkeypatch):
    """Background approval errors persist status='failed' and track_data['error'] without raising HTTPException."""
    from services.metadata_enhancer import MetadataWriteVerificationError

    work_db = isolated_review_env["work_db"]
    download_dir = isolated_review_env["download_dir"]

    staged_file = download_dir / "broken_tag.flac"
    staged_file.write_bytes(b"fLaC" + b"\x00" * 64)

    with work_db.session_scope() as session:
        task = ReviewTask(
            file_path=str(staged_file),
            status="pending",
            confidence_score=0.8,
            track_data={"title": "Original", "artist": "Artist A"},
        )
        session.add(task)
        session.flush()
        task_id = task.id

    mock_enhancer = MagicMock()
    mock_enhancer.tag_file_verified.side_effect = MetadataWriteVerificationError("checksum mismatch on disk")
    monkeypatch.setattr("web.routes.metadata_review.get_metadata_enhancer", lambda: mock_enhancer)
    monkeypatch.setattr("echosync_core.extract_metadata", lambda _p: {"duration_ms": 180000})

    res = approve_review_queue_item(
        task_id,
        ApproveReviewQueueRequest(metadata={"title": "Updated", "artist": "Artist A"}),
    )
    assert res["success"] is True
    assert res["status"] == "approved_queued"

    with work_db.session_scope() as session:
        updated = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
        assert updated is not None
        assert updated.status == "failed"
        assert "checksum mismatch on disk" in updated.track_data.get("error", "")
        serialized = _serialize_task(updated, current_metadata={})
        assert serialized["status"] == "failed"
        assert "checksum mismatch on disk" in (serialized["error"] or "")


def test_background_approval_import_failure_persists_failed_state(isolated_review_env, monkeypatch):
    """Any post-tagging exception during background approval persists status='failed' and error message."""
    work_db = isolated_review_env["work_db"]
    download_dir = isolated_review_env["download_dir"]

    staged_file = download_dir / "import_fail.flac"
    staged_file.write_bytes(b"fLaC" + b"\x00" * 64)

    with work_db.session_scope() as session:
        task = ReviewTask(
            file_path=str(staged_file),
            status="pending",
            confidence_score=0.9,
            track_data={"title": "Song", "artist": "Artist B"},
        )
        session.add(task)
        session.flush()
        task_id = task.id

    mock_enhancer = MagicMock()
    mock_enhancer.tag_file_verified.return_value = True
    monkeypatch.setattr("web.routes.metadata_review.get_metadata_enhancer", lambda: mock_enhancer)
    monkeypatch.setattr("echosync_core.extract_metadata", lambda _p: {"duration_ms": 200000})
    monkeypatch.setattr(
        "web.routes.metadata_review._import_single_file",
        MagicMock(side_effect=RuntimeError("database write failure")),
    )

    res = approve_review_queue_item(
        task_id,
        ApproveReviewQueueRequest(metadata={"title": "Song", "artist": "Artist B"}),
    )
    assert res["success"] is True

    with work_db.session_scope() as session:
        updated = session.query(ReviewTask).filter(ReviewTask.id == task_id).first()
        assert updated is not None
        assert updated.status == "failed"
        assert updated.track_data.get("error") == "database write failure"


def test_reject_review_task_routes_deletion_through_gatekeeper(isolated_review_env, monkeypatch):
    """Rejecting a review task deletes physical files strictly via Gatekeeper, including poor_metadata_dir."""
    work_db = isolated_review_env["work_db"]
    poor_dir = isolated_review_env["poor_dir"]
    download_dir = isolated_review_env["download_dir"]

    poor_file = poor_dir / "bad_metadata.flac"
    poor_file.write_bytes(b"audio bytes")
    dl_file = download_dir / "dl_reject.flac"
    dl_file.write_bytes(b"download bytes")

    with work_db.session_scope() as session:
        t1 = ReviewTask(file_path=str(poor_file), status="pending", track_data={"title": "Bad"})
        t2 = ReviewTask(file_path=str(dl_file), status="pending", track_data={"title": "DL"})
        session.add_all([t1, t2])
        session.flush()
        t1_id, t2_id = t1.id, t2.id

    published = []
    monkeypatch.setattr("core.event_bus.event_bus.publish", lambda *args, **kwargs: published.append((args, kwargs)))

    # Real Gatekeeper deletion on poor_metadata_dir (not in default Gatekeeper roots)
    app = create_app(testing=True)
    with TestClient(app) as client:
        resp1 = client.post(f"/api/v1/core/metadata_review/{t1_id}/reject")
        assert resp1.status_code == 200
        assert resp1.json()["status"] == "rejected"
        assert not poor_file.exists()

        # Verify Gatekeeper.authorize_and_execute is invoked (not os.unlink)
        with patch("core.io_gatekeeper.Gatekeeper.authorize_and_execute") as mock_gk:
            resp2 = client.post(f"/api/v1/core/metadata_review/{t2_id}/reject")
            assert resp2.status_code == 200
            mock_gk.assert_called_once()
            call_kwargs = mock_gk.call_args.kwargs
            assert call_kwargs["operation"] == "delete_file"
            assert Path(call_kwargs["target_uri"]).resolve() == dl_file.resolve()

    with work_db.session_scope() as session:
        assert session.query(ReviewTask).filter(ReviewTask.id == t1_id).first().status == "rejected"
        assert session.query(ReviewTask).filter(ReviewTask.id == t2_id).first().status == "rejected"
    assert len(published) == 2


def test_metadata_review_enforces_nanoid_media_id_validation(isolated_review_env):
    """Media-targeted review endpoints reject integer PKs and path strings while accepting NanoIDs."""
    music_db = isolated_review_env["music_db"]
    download_dir = isolated_review_env["download_dir"]

    audio_file = download_dir / "valid_track.flac"
    audio_file.write_bytes(b"audio content")
    valid_mid = f"M_{generate_nanoid(8)}"

    with music_db.session_scope() as session:
        artist = Artist(name="Nano Artist")
        session.add(artist)
        session.flush()
        track = Track(sync_id=f"S_{generate_nanoid(8)}", title="Nano Track", artist_id=artist.id)
        session.add(track)
        session.flush()
        session.add(
            LocalMedia(
                media_id=valid_mid,
                track_id=track.id,
                file_path=_canonicalize_path(str(audio_file)),
                file_format="flac",
            )
        )

    assert _get_media_file_path("/etc/passwd") is None
    assert _get_media_file_path("123") is None
    assert _get_media_file_path(valid_mid) == _canonicalize_path(str(audio_file))

    app = create_app(testing=True)
    with TestClient(app) as client:
        for bad_id in ("123", "-42", " 999 ", "/music/song.flac", r"C:\music\song.flac", "../secret", "virtual://1", "song.mp3"):
            r1 = client.post("/api/v1/core/metadata_review", json={"media_id": bad_id})
            assert r1.status_code == 400, f"Expected 400 for create media_id={bad_id!r}, got {r1.status_code}"

            r2 = client.post(
                "/api/v1/review/tasks",
                json={"file_path": str(audio_file), "track_data": {"media_id": bad_id}},
            )
            assert r2.status_code == 400, f"Expected 400 for nested track_data media_id={bad_id!r}"

        created = client.post("/api/v1/core/metadata_review", json={"media_id": valid_mid})
        assert created.status_code == 200
        task_id = created.json()["id"]

        for bad_id in ("456", "/var/music/other.flac", r"D:\audio\x.mp3", "virtual://track"):
            patch_bad = client.patch(f"/api/v1/core/metadata_review/{task_id}/save", json={"media_id": bad_id})
            assert patch_bad.status_code == 400

            patch_nested = client.patch(
                f"/api/v1/core/metadata_review/{task_id}/save",
                json={"metadata": {"media_id": bad_id}},
            )
            assert patch_nested.status_code == 400

            approve_bad = client.post(
                f"/api/v1/core/metadata_review/{task_id}/approve",
                json={"metadata": {"media_id": bad_id}},
            )
            assert approve_bad.status_code == 400


def test_deletion_batch_veto_uses_local_media_external_identifier_join(tmp_path, monkeypatch):
    """Trending veto joins LocalMedia -> ExternalIdentifier.plugin_item_id and queries PlaybackHistory.plugin_item_id."""
    music_db = MusicDatabase(str(tmp_path / "music_del.db"))
    Base.metadata.create_all(music_db.engine)
    work_db = WorkingDatabase(str(tmp_path / "working_del.db"))
    WorkingBase.metadata.create_all(work_db.engine)

    monkeypatch.setattr(deletion_mod, "get_working_database", lambda: work_db)
    monkeypatch.setattr("database.music_database.get_database", lambda *a, **kw: music_db)

    now = utc_now()
    sync_trending = "sync_trend_001"
    sync_cold = "sync_cold_002"
    mid_trend_1 = f"m_{generate_nanoid(6)}"
    mid_trend_2 = f"m_{generate_nanoid(6)}"
    mid_cold = f"m_{generate_nanoid(6)}"

    with music_db.session_scope() as m_sess:
        artist = Artist(name="Trending Artist")
        m_sess.add(artist)
        m_sess.flush()

        t_trend = Track(sync_id=sync_trending, title="Hot Song", artist_id=artist.id)
        t_cold = Track(sync_id=sync_cold, title="Cold Song", artist_id=artist.id)
        m_sess.add_all([t_trend, t_cold])
        m_sess.flush()

        m_sess.add_all(
            [
                LocalMedia(media_id=mid_trend_1, track_id=t_trend.id, file_path=str(tmp_path / "hot1.flac")),
                LocalMedia(media_id=mid_trend_2, track_id=t_trend.id, file_path=str(tmp_path / "hot2.mp3")),
                LocalMedia(media_id=mid_cold, track_id=t_cold.id, file_path=str(tmp_path / "cold.mp3")),
            ]
        )
        m_sess.flush()

        m_sess.add_all(
            [
                ExternalIdentifier(media_id=mid_trend_1, plugin_source="srv_a", plugin_item_id="item_hot_1"),
                ExternalIdentifier(media_id=mid_trend_2, plugin_source="srv_b", plugin_item_id="item_hot_2"),
                ExternalIdentifier(media_id=mid_cold, plugin_source="srv_a", plugin_item_id="item_cold_1"),
            ]
        )

    with work_db.session_scope() as w_sess:
        acc = Account(plugin_id=zlib.crc32(b"echosync.srv_a") & 0xFFFFFFFF, remote_account_id="u1")
        w_sess.add(acc)
        w_sess.flush()
        w_sess.add_all(
            [
                UserTrackState(account_id=acc.id, sync_id=sync_trending),
                UserTrackState(account_id=acc.id, sync_id=sync_cold),
            ]
        )
        # 5 recent listens for item_hot_1 (and 1 old listen for item_cold_1)
        for idx in range(5):
            w_sess.add(
                PlaybackHistory(
                    user_id="u1",
                    plugin_item_id="item_hot_1",
                    listened_at=now - timedelta(days=1, minutes=idx),
                )
            )
        w_sess.add(
            PlaybackHistory(
                user_id="u1",
                plugin_item_id="item_cold_1",
                listened_at=now - timedelta(days=45),
            )
        )

    try:
        res = apply_lifecycle_actions_batch(
            {
                sync_trending: {"action": DELETE_MONTH_END, "score_10": 1.0},
                sync_cold: {"action": DELETE_MONTH_END, "score_10": 1.0},
            }
        )
        assert res[sync_trending]["status"] == "KEEP_EXEMPT"
        assert res[sync_cold]["status"] == "DELETE_STAGED"

        with work_db.session_scope() as w_sess:
            st_hot = w_sess.query(UserTrackState).filter_by(sync_id=sync_trending).first()
            st_cold = w_sess.query(UserTrackState).filter_by(sync_id=sync_cold).first()
            assert st_hot.admin_exempt_deletion is True
            assert st_hot.lifecycle_action is None
            assert st_cold.lifecycle_action == DELETE_MONTH_END
    finally:
        music_db.dispose()
        work_db.dispose()


def test_process_lifecycle_actions_admin_force_upgrade_not_inverted(tmp_path, monkeypatch):
    """admin_force_upgrade=True must execute upgrades (never skip them) and protect from deletion."""
    work_db = WorkingDatabase(str(tmp_path / "working_proc.db"))
    WorkingBase.metadata.create_all(work_db.engine)
    monkeypatch.setattr(deletion_mod, "get_working_database", lambda: work_db)

    now = utc_now()
    monkeypatch.setattr(
        "core.settings.config_manager.get",
        lambda key, default=None: {
            "auto_delete": True,
            "auto_upgrade": False,
            "upgrade_quality_profile_id": "lossless",
        }
        if key == "manager"
        else default,
    )

    upgraded_calls: list[tuple[str, str | None]] = []
    deleted_calls: list[str] = []

    monkeypatch.setattr(
        deletion_mod,
        "execute_upgrade_now",
        lambda sync_id, quality_profile_id=None: (
            upgraded_calls.append((sync_id, quality_profile_id)) or {"success": True}
        ),
    )
    monkeypatch.setattr(
        deletion_mod,
        "execute_delete_now",
        lambda sync_id: deleted_calls.append(sync_id) or {"success": True},
    )

    with work_db.session_scope() as w_sess:
        acc = Account(plugin_id=zlib.crc32(b"echosync.test") & 0xFFFFFFFF, remote_account_id="u1")
        w_sess.add(acc)
        w_sess.flush()

        w_sess.add_all(
            [
                # Forced upgrade even though queued just now and auto_upgrade=False -> MUST run
                UserTrackState(
                    account_id=acc.id,
                    sync_id="sync_force_now",
                    lifecycle_action=UPGRADE_WEEK_END,
                    lifecycle_queued_at=now,
                    admin_force_upgrade=True,
                ),
                # Normal upgrade when auto_upgrade=False -> MUST skip
                UserTrackState(
                    account_id=acc.id,
                    sync_id="sync_normal_skip",
                    lifecycle_action=UPGRADE_WEEK_END,
                    lifecycle_queued_at=now - timedelta(days=10),
                    admin_force_upgrade=False,
                ),
                # Exempt deletion -> MUST skip
                UserTrackState(
                    account_id=acc.id,
                    sync_id="sync_exempt_del",
                    lifecycle_action=DELETE_MONTH_END,
                    lifecycle_queued_at=now - timedelta(days=35),
                    admin_exempt_deletion=True,
                ),
                # Forced upgrade mistakenly still tagged DELETE_MONTH_END -> MUST NOT delete
                UserTrackState(
                    account_id=acc.id,
                    sync_id="sync_force_no_del",
                    lifecycle_action=DELETE_MONTH_END,
                    lifecycle_queued_at=now - timedelta(days=35),
                    admin_force_upgrade=True,
                ),
            ]
        )

    try:
        summary = process_lifecycle_actions()
        assert upgraded_calls == [("sync_force_now", "lossless")]
        assert deleted_calls == []
        assert summary["upgrade_processed"] == 1
        assert summary["upgrade_skipped"] == 1
        assert summary["delete_processed"] == 0
        assert summary["delete_skipped"] == 2
    finally:
        work_db.dispose()


def test_state_listener_deterministic_plugin_resolution(tmp_path, monkeypatch):
    """StateListenerService resolves plugin_id via Principal, user_managed_accounts, config.db, and zlib.crc32."""
    close_config_database()
    work_db = WorkingDatabase(str(tmp_path / "working_sl.db"))
    WorkingBase.metadata.create_all(work_db.engine)
    cfg_db = ConfigDatabase(str(tmp_path / "config_sl.db"))

    monkeypatch.setattr(consensus_mod, "get_working_database", lambda: work_db)
    monkeypatch.setattr(deletion_mod, "get_working_database", lambda: work_db)

    class _Bus:
        def __init__(self):
            self.events = []

        def subscribe(self, *_a, **_kw):
            pass

        def publish(self, payload):
            self.events.append(payload)

    node_a_pid = zlib.crc32(b"echosync.media_node_a") & 0xFFFFFFFF
    custom_srv_pid = zlib.crc32(b"echosync.custom_srv") & 0xFFFFFFFF
    alt_srv_pid = zlib.crc32(b"echosync.alt_srv") & 0xFFFFFFFF

    user = cfg_db.create_user("listener_user", password="correct horse battery staple", roles=["member"])
    cfg_db.assign_managed_account(user["id"], node_a_pid, "managed-77")
    cfg_db.register_service("EchoSync.custom_srv", "media_server", "Custom Server", plugin_id=custom_srv_pid)

    listener = StateListenerService(event_bus=_Bus(), session_factory=work_db.SessionLocal, config_db=cfg_db)

    try:
        # 1. Active Principal + user_managed_accounts resolution when provider='unknown'
        principal = Principal(
            user_id=user["id"],
            username="listener_user",
            principal_type="user",
            roles=("member",),
            scopes=frozenset(),
        )
        with principal_scope(principal):
            listener.handle_track_rated(
                {
                    "event": "TRACK_RATED",
                    "sync_id": "sync_sl_1",
                    "data": {"rating": 5.0, "user_id": "managed-77", "provider": "unknown"},
                }
            )

        # 2. ConfigDB services table resolution
        listener.handle_track_rated(
            {
                "event": "TRACK_RATED",
                "sync_id": "sync_sl_2",
                "data": {"rating": 4.0, "user_id": "u_custom", "provider": "custom_srv"},
            }
        )

        # 3. Plugin Principal resolution
        plugin_pid = zlib.crc32(b"echosync.plugin_actor") & 0xFFFFFFFF
        with principal_scope(
            Principal(
                user_id=None,
                username="plugin_actor",
                principal_type="plugin",
                plugin_id=plugin_pid,
            )
        ):
            listener.handle_track_rated(
                {
                    "event": "TRACK_RATED",
                    "sync_id": "sync_sl_3",
                    "data": {"rating": 3.5, "user_id": "u_plugin", "provider": "unknown"},
                }
            )

        # 4. Deterministic zlib.crc32 fallback (never hardcoded plugin_id=1)
        listener.handle_track_rated(
            {
                "event": "TRACK_RATED",
                "sync_id": "sync_sl_4",
                "data": {"rating": 2.5, "user_id": "u_alt", "provider": "alt_srv"},
            }
        )

        with work_db.session_scope() as session:
            accounts = {a.remote_account_id: a.plugin_id for a in session.query(Account).all()}
            assert accounts["managed-77"] == node_a_pid
            assert accounts["u_custom"] == custom_srv_pid
            assert accounts["u_plugin"] == plugin_pid
            assert accounts["u_alt"] == alt_srv_pid
            assert 1 not in accounts.values()
    finally:
        work_db.dispose()
        close_config_database()


def test_bounded_ttl_cache_eviction_ttl_and_concurrency():
    """BoundedTTLCache enforces max_size LRU eviction, TTL expiry, and thread-safe operations."""
    now = [100.0]
    cache: BoundedTTLCache[str, dict] = BoundedTTLCache(max_size=3, ttl_seconds=10.0, clock=lambda: now[0])

    cache["a"] = {"v": 1}
    cache["b"] = {"v": 2}
    cache["c"] = {"v": 3}
    # Access "a" so "b" becomes least recently used
    assert cache["a"] == {"v": 1}
    cache["d"] = {"v": 4}

    assert len(cache) == 3
    assert "b" not in cache
    assert set(cache.keys()) == {"a", "c", "d"}

    # Advance past TTL -> entries expire
    now[0] += 11.0
    assert len(cache) == 0
    assert cache.get("a") is None
    assert "c" not in cache

    # Concurrency stress test under threading.Lock
    conc_cache: BoundedTTLCache[str, dict] = BoundedTTLCache(max_size=32, ttl_seconds=60.0)
    errors: list[Exception] = []

    def worker(tid: int) -> None:
        try:
            for i in range(100):
                k = f"k_{tid}_{i}"
                conc_cache[k] = {"status": "queued", "worker": tid}
                conc_cache.update_item(k, {"status": "running"})
                _ = conc_cache.get(k)
                _ = list(conc_cache.items())
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(idx,)) for idx in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    assert len(conc_cache) <= 32


def test_playlist_sync_match_trace_and_analysis_jobs_bounded(monkeypatch):
    """MATCH_TRACE_CACHE and ANALYSIS_JOBS share bounded thread-safe TTL cache semantics."""
    assert isinstance(MATCH_TRACE_CACHE, BoundedTTLCache)
    assert isinstance(ANALYSIS_JOBS, BoundedTTLCache)
    assert playlists_route.ANALYSIS_JOBS is ANALYSIS_JOBS

    clear_match_trace_cache()
    ANALYSIS_JOBS.clear()
    try:
        cache_match_trace({"title": "Track One", "artist": "Artist One", "duration_ms": 180000}, {"ok": True})
        assert get_cached_match_trace("Track One", "Artist One", 180000) == {"ok": True}

        # Verify start_analyze_job / get_analyze_job work with bounded ANALYSIS_JOBS
        monkeypatch.setattr("core.nexus_framework.plugin_loader.get_plugin_capabilities", lambda _s: object())

        class ImmediateQueue:
            def register_job(self, name, func, **_kw):
                self._fn = func

            def execute_job_now(self, _name):
                self._fn()

        monkeypatch.setattr(playlists_route, "job_queue", ImmediateQueue())
        monkeypatch.setattr(
            playlists_route,
            "_analyze_playlists_internal",
            lambda *a, **kw: {"summary": {"total_tracks": 1}},
        )

        start_res = playlists_route.start_analyze_job(
            playlists_route.PlaylistAnalyzeSchema(
                source="src_plugin",
                target="dst_plugin",
                playlists=[{"id": "p1", "name": "P1", "tracks": []}],
            )
        )
        assert start_res["accepted"] is True
        job_id = start_res["job_id"]

        poll_res = playlists_route.get_analyze_job(job_id, None)
        assert poll_res["status"] == "finished"
        assert poll_res["result"] == {"summary": {"total_tracks": 1}}
    finally:
        clear_match_trace_cache()
        ANALYSIS_JOBS.clear()
