import logging
from typing import Optional

from core.tiered_logger import get_logger
from services.library_reorganizer import LibraryReorganizerService
from core.event_bus import event_bus
from core.job_queue import register_job

logger = get_logger("jobs.reorganize_library")

# Defining a BaseJob interface if it doesn't already exist in the system,
# to provide the requested update_progress functionality.
class BaseJob:
    def update_progress(self, current: int, total: int, status: str = ""):
        event_bus.publish("job_progress", {
            "job_name": self.__class__.__name__,
            "current": current,
            "total": total,
            "status": status,
            "percentage": round((current / total) * 100, 1) if total > 0 else 0
        })

class ReorganizeLibraryJob(BaseJob):
    def execute(self, *args, **kwargs):
        logger.info("Starting library reorganization job")
        service = LibraryReorganizerService()
        
        # Use the inherited progress method as the callback
        service.reorganize_library(progress_callback=self.update_progress)
        
        logger.info("Library reorganization job completed")

def register_reorganize_library_job(interval_seconds: Optional[int] = None, enabled: bool = True):
    """
    Registration snippet for the global JobRegistry (job_queue).
    """
    job_instance = ReorganizeLibraryJob()
    
    register_job(
        name="reorganize_library",
        func=job_instance.execute,
        interval_seconds=interval_seconds,
        enabled=enabled
    )
