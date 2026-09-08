"""System watcher utilities and suppression registry re-export."""

from services.library_watcher import is_path_suppressed, suppress_path

__all__ = ["is_path_suppressed", "suppress_path"]
