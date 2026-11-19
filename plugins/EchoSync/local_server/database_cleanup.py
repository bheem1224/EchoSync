# plugins/EchoSync/local_server/database_cleanup.py

from pathlib import Path

from core.nexus_framework.sdk import compute_plugin_crc32, sdk
from core.settings import config_manager
from core.task_manager.task_queue import db_write_lease, register_job
from core.tiered_logger import get_logger

PLUGIN_NAMESPACE = "EchoSync.local_server"
PLUGIN_CRC32 = compute_plugin_crc32(PLUGIN_NAMESPACE)
logger = get_logger("jobs.database_cleanup", plugin_id=PLUGIN_CRC32)

try:
    from core.jobs.reorganize_library_job import BaseJob
except ImportError:

    class BaseJob:
        def update_progress(self, current: int, total: int, status: str = ""):
            pass


def _canonicalize_path(file_path: str) -> str:
    """Produce a deterministic canonical form for a file path."""
    if not file_path or file_path.startswith("virtual://"):
        return file_path
    try:
        return Path(file_path).resolve().as_posix()
    except Exception:
        return file_path


def get_database():
    """Governed SDK accessor for canonical library database."""
    return sdk.library.get_database()


class DatabaseCleanupJob(BaseJob):
    """
    A manual dev utility designed to correct database drift by aggressively
    evicting ghost paths, deduplicating identical tracks, and pruning structural orphans.
    """

    def execute(self, *args, **kwargs):
        logger.info("Starting manual Database Cleanup Job...")
        db = get_database()
        skip_rogue = hasattr(Path, "PYTEST_CURRENT_TEST_ENV")
        sanctioned_prefixes = tuple(config_manager.get("SANCTIONED_PATH_PREFIXES", ["/data/library/"]))

        with db_write_lease(task_name=f"plugin_{PLUGIN_CRC32}"):
            stats = sdk.library.cleanup_library_database(
                db=db,
                progress_callback=self.update_progress,
                canonicalize_path=_canonicalize_path,
                sanctioned_prefixes=sanctioned_prefixes,
                skip_rogue_sweep=skip_rogue,
            )

        logger.info(
            "Manual Database Cleanup Job finished successfully: %s",
            stats,
        )


def register_database_cleanup_job(enabled: bool = True):
    """Registration snippet for the global JobRegistry (job_queue)."""
    job_instance = DatabaseCleanupJob()

    register_job(
        name="database_cleanup",
        func=job_instance.execute,
        interval_seconds=315360000,
        start_after=315360000,
        enabled=enabled,
    )
