import time

from core.jobs.decouple_media_job import DecoupleMediaJob, register_decouple_media_job
from core.task_manager.supervisor import supervisor
from core.task_manager.system_jobs import register_all_system_jobs
from core.task_manager.task_queue import job_queue
from database import _canonicalize_path
from database.music_database import Artist, Base, LocalMedia, Track, get_database


def test_decouple_media_job_registration_and_dormancy():
    """Verify that system.decouple_collapsed_media is registered with a dormant 1000-day schedule."""
    # Register job
    register_decouple_media_job(interval_seconds=86400 * 1000, enabled=True)

    with job_queue._lock:
        job = job_queue._jobs.get("system.decouple_collapsed_media")
        assert job is not None, (
            "Job system.decouple_collapsed_media must be registered in job_queue"
        )
        assert job.interval_seconds == 86400 * 1000
        # Ensure job start time is scheduled far in the future (> 900 days away, not immediate)
        now = time.time()
        assert job.next_run > now + (86400 * 900), "Job must not execute on startup"


def test_register_all_system_jobs_includes_decouple_media():
    """Verify register_all_system_jobs successfully includes system.decouple_collapsed_media."""
    register_all_system_jobs()

    with job_queue._lock:
        job = job_queue._jobs.get("system.decouple_collapsed_media")
        assert job is not None
        assert job.interval_seconds == 86400 * 1000


def test_decouple_media_job_execution():
    """Verify executing DecoupleMediaJob decouples multi-edition tracks and cleans up supervisor."""
    db = get_database()
    Base.metadata.drop_all(db.engine)
    Base.metadata.create_all(db.engine)

    with db.session_scope() as session:
        artist = Artist(name="Capital Cities")
        session.add(artist)
        session.flush()

        collapsed_track = Track(
            id=9819,
            sync_id="g8a9b1c2",
            title="Safe and Sound",
            artist_id=artist.id,
            duration=343000,
        )
        session.add(collapsed_track)
        session.flush()

        m1 = LocalMedia(
            media_id="med_0001",
            track_id=9819,
            file_path=_canonicalize_path("/music/Capital Cities/Safe and Sound.flac"),
            file_format="FLAC",
        )
        m2 = LocalMedia(
            media_id="med_0002",
            track_id=9819,
            file_path=_canonicalize_path(
                "/music/Capital Cities/Safe and Sound (Remix).flac"
            ),
            file_format="FLAC",
        )
        session.add_all([m1, m2])

    # Execute job
    progress_updates = []

    def on_progress(cur, tot, status):
        progress_updates.append((cur, tot, status))

    job = DecoupleMediaJob()
    job.update_progress = on_progress
    result = job.execute()

    assert result["status"] == "completed"
    assert result["decoupled_count"] == 1

    # Verify supervisor unregisters cleanly
    active_processes = supervisor.get_active_processes_with_ids()
    active_owners = [p.get("owner_id") for p in active_processes]
    assert "system.decouple_collapsed_media" not in active_owners

    # Verify tracks were dissociated in DB
    with db.session_scope() as session:
        tracks = session.query(Track).all()
        assert len(tracks) == 2

        m1_refreshed = session.query(LocalMedia).filter_by(media_id="med_0001").first()
        m2_refreshed = session.query(LocalMedia).filter_by(media_id="med_0002").first()
        assert m1_refreshed.track_id != m2_refreshed.track_id
