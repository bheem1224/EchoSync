"""
Ingestion Orchestrator (core/orchestrator/ingestion.py).
Streams PyDict telemetry payloads from echosync_core / Gatekeeper and performs batched 1,000-row UPSERT transactions into database.
"""
from typing import Callable, List, Dict, Any, Optional
import logging
from sqlalchemy.orm import Session
from database.music_database import get_database
from core.models import EchoSyncTrack
from core.database.repositories.track_repo import bulk_upsert_tracks

logger = logging.getLogger("ingestion_orchestrator")


class IngestionOrchestrator:
    """
    Orchestrates high-throughput telemetry ingestion with 1,000-row chunking to prevent database locking.
    """

    def __init__(self, batch_size: int = 1000, session_factory: Optional[Callable[[], Session]] = None):
        self.batch_size = batch_size
        self.session_factory = session_factory or (lambda: get_database().get_session())

    def ingest_telemetry_batch(self, pydict_batch: List[Dict[str, Any]]) -> int:
        """
        Process a list of PyDict records yielded by FFI, parse into EchoSyncTrack models, and UPSERT into database.
        """
        if not pydict_batch:
            return 0

        tracks = []
        for raw_dict in pydict_batch:
            try:
                track = EchoSyncTrack.model_validate(raw_dict)
                tracks.append(track)
            except Exception as e:
                logger.warning(f"Skipping invalid telemetry record: {e}")

        if not tracks:
            return 0

        session = self.session_factory()
        try:
            total_upserted = 0
            # Process in 1,000-row chunks
            for i in range(0, len(tracks), self.batch_size):
                chunk = tracks[i:i + self.batch_size]
                affected = bulk_upsert_tracks(session, chunk)
                session.commit()
                total_upserted += affected

            logger.info(f"Ingested {total_upserted} tracks across {len(tracks)} telemetry records.")
            return total_upserted
        except Exception as e:
            session.rollback()
            logger.error(f"Failed during ingestion transaction: {e}", exc_info=True)
            raise
        finally:
            session.close()

    def create_telemetry_callback(self) -> Any:
        """
        Create a streaming telemetry callback function that buffers incoming PyDict batches
        and triggers a 1,000-row UPSERT transaction whenever the buffer reaches 1,000 records.
        """
        buffer: List[Dict[str, Any]] = []

        def callback(pydict_list: List[Dict[str, Any]]) -> None:
            buffer.extend(pydict_list)
            while len(buffer) >= self.batch_size:
                chunk = buffer[:self.batch_size]
                del buffer[:self.batch_size]
                self.ingest_telemetry_batch(chunk)

        def flush() -> int:
            if buffer:
                count = self.ingest_telemetry_batch(buffer)
                buffer.clear()
                return count
            return 0

        callback.flush = flush  # type: ignore
        return callback
