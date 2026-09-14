"""
Legacy Compatibility Forwarder for EchoSync Track Model.

Re-exports canonical track representations from core.db.echo_sync_track so that
older plugin releases (e.g., v2.4.2 artifacts) continue to resolve without ModuleNotFoundError
during live-swaps and runtime execution.
"""

from core.db.echo_sync_track import (
    DownloadStatus,
    EchosyncTrack,
    QualityTag,
)
from core.db.echo_sync_track import (
    EchosyncTrack as Track,
)

__all__ = [
    "DownloadStatus",
    "EchosyncTrack",
    "QualityTag",
    "Track",
]
