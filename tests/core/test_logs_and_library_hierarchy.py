"""Tests for the in-app log viewer API and flat-query library hierarchy optimization."""

from datetime import date
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from database.music_database import Album, Artist, Base, LocalMedia, MusicDatabase, Track
from web.routes.system import router as system_router


def test_system_logs_parsing_filtering_and_download(tmp_path: Path):
    log_file = tmp_path / "app.log"
    log_file.write_text(
        "\n".join(
            [
                "2026-11-21 15:56:29,100 - plex_routes - INFO - start_auth:45 - Plex OAuth started",
                "2026-11-21 15:56:30,200 - spotify_client - WARNING - refresh:88 - Token expiring soon",
                "2026-11-21 15:56:31,300 - acoustid_routes - ERROR - save_config:72 - Failed to persist key",
                "Traceback (most recent call last):",
                '  File "/app/routes.py", line 72, in save_config',
                "RuntimeError: disk full",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "debug.log").write_text(
        "2026-11-21 15:56:32,000 - worker - DEBUG - tick:10 - Heartbeat ok\n",
        encoding="utf-8",
    )

    app = FastAPI()
    app.include_router(system_router)
    # Bypass scope check in isolated router test while verifying route behavior
    from web.auth import Principal, require_auth

    app.dependency_overrides[require_auth] = lambda: Principal(
        principal_type="user", user_id=1, username="admin", roles=["admin"], scopes={"service:system:edit"}
    )

    with patch("web.routes.system.get_log_dir", return_value=tmp_path):
        client = TestClient(app)

        resp = client.get("/api/v1/system/logs?source=app.log")
        assert resp.status_code == 200
        data = resp.json()
        assert data["active_file"] == "app.log"
        assert data["available_files"][:2] == ["app.log", "debug.log"]
        assert data["total_entries"] == 3
        assert data["level_counts"]["ERROR"] == 1
        assert data["level_counts"]["WARNING"] == 1
        assert data["level_counts"]["INFO"] == 1
        # Traceback continuation lines should be attached to the ERROR entry
        err_entry = [e for e in data["logs"] if e["level"] == "ERROR"][0]
        assert "RuntimeError: disk full" in err_entry["details"]

        # Level + logger filtering
        err_only = client.get("/api/v1/system/logs?source=app.log&level=ERROR&logger_name=acoustid")
        assert err_only.status_code == 200
        assert len(err_only.json()["logs"]) == 1

        # Regex search + invalid regex handling
        regex_ok = client.get("/api/v1/system/logs?source=app.log&search=OAuth.*started&regex=true")
        assert regex_ok.status_code == 200
        assert len(regex_ok.json()["logs"]) == 1

        regex_bad = client.get("/api/v1/system/logs?source=app.log&search=[unclosed&regex=true")
        assert regex_bad.status_code == 400

        # Download endpoint
        dl = client.get("/api/v1/system/logs/download?source=debug.log")
        assert dl.status_code == 200
        assert "Heartbeat ok" in dl.text


def test_get_library_hierarchy_flat_query(tmp_path: Path):
    db_path = tmp_path / "music.db"
    db = MusicDatabase(str(db_path))
    Base.metadata.create_all(db.engine)

    with db.session_scope() as session:
        artist_with_media = Artist(name="Artist One")
        artist_without_media = Artist(name="Ghost Artist")
        session.add_all([artist_with_media, artist_without_media])
        session.flush()

        album = Album(artist_id=artist_with_media.id, title="First Album", release_date=date(2024, 5, 1))
        session.add(album)
        session.flush()

        t1 = Track(
            sync_id="tr_001",
            artist_id=artist_with_media.id,
            album_id=album.id,
            title="Track One",
            duration=200,
            track_number=1,
            disc_number=1,
        )
        t_loose = Track(
            sync_id="tr_002",
            artist_id=artist_with_media.id,
            album_id=None,
            title="Loose Track",
            duration=180,
            track_number=1,
            disc_number=1,
        )
        t_no_media = Track(
            sync_id="tr_003",
            artist_id=artist_without_media.id,
            album_id=None,
            title="Missing File",
            duration=150,
            track_number=1,
            disc_number=1,
        )
        session.add_all([t1, t_loose, t_no_media])
        session.flush()

        session.add(LocalMedia(media_id="lm_001", track_id=t1.id, file_path="/music/t1.flac"))
        session.add(LocalMedia(media_id="lm_002", track_id=t_loose.id, file_path="/music/t2.flac"))

    hierarchy = db.get_library_hierarchy()
    assert len(hierarchy) == 1
    assert hierarchy[0]["name"] == "Artist One"
    assert len(hierarchy[0]["albums"]) == 2
    assert hierarchy[0]["albums"][0]["title"] == "First Album"
    assert hierarchy[0]["albums"][0]["year"] == 2024
    assert hierarchy[0]["albums"][0]["tracks"][0]["media_ids"] == ["lm_001"]
    assert hierarchy[0]["albums"][1]["title"] == "Unknown Album"
    assert hierarchy[0]["albums"][1]["tracks"][0]["media_ids"] == ["lm_002"]
