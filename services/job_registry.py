"""
Job Registry convenience module for EchoSync.
Exposes standard system maintenance and lifecycle jobs for background scheduling and triggering.
"""

from core.jobs.decouple_media_job import (
    DecoupleMediaJob,
    register_decouple_media_job,
)
from services.maintenance_service import run_media_decoupling_job

__all__ = [
    "DecoupleMediaJob",
    "register_decouple_media_job",
    "run_media_decoupling_job",
]
