import logging
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.nexus_framework.plugin_loader import PluginRegistry
from core.settings import config_manager
from database import MusicDatabase
from database.music_database import Track
from services.library_sync_service import LibrarySyncService

logging.basicConfig(level=logging.INFO)


def run_diagnostic():
    db = MusicDatabase("data/music.db")

    # Initialize basic config explicitly for the provider
    config_manager.set("LOCAL_MUSIC_DIRS", ["data/music"])

    print("Loading plugins...")
    registry = PluginRegistry()
    registry.discover_plugins()

    provider_class = registry.get_provider("EchoSync.local_server")
    provider = provider_class()

    # Count before
    with db.session_scope() as session:
        count_before = session.query(Track).count()
        print(f"Tracks in DB BEFORE import: {count_before}")

    print("Starting library sync...")
    worker = LibrarySyncService(database_path="data/music.db")
    worker.sync_library()

    # Count after
    with db.session_scope() as session:
        count_after = session.query(Track).count()
        print(f"Tracks in DB AFTER import: {count_after}")


if __name__ == "__main__":
    run_diagnostic()
