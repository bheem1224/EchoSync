"""Explicit PipelineContext stage tracking and capability-gated hook contracts."""

from __future__ import annotations

import contextlib
import contextvars
import time
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PipelineStage(str, Enum):
    """Canonical pipeline stages replacing legacy unsubscribed broadcast hooks."""

    INGEST_PRE_TRACK = "ingest.pre_track"
    INGEST_POST_TRACK = "ingest.post_track"
    FINGERPRINT_PRE_EXTRACT = "fingerprint.pre_extract"
    FINGERPRINT_POST_EXTRACT = "fingerprint.post_extract"
    METADATA_REQUIREMENTS = "metadata.requirements"
    METADATA_EXTERNAL_FETCH = "metadata.external_fetch"
    METADATA_POST_ENRICHMENT = "metadata.post_enrichment"
    SEARCH_PRE_PROVIDER = "search.pre_provider"
    SEARCH_EXPANSION = "search.expansion"
    NORMALIZE_PRE_TITLE = "normalize.pre_title"
    NORMALIZE_PRE_TEXT = "normalize.pre_text"
    SCORING_WEIGHTS_CALCULATE = "scoring.weights_calculate"
    SCORING_MODIFIER = "scoring.modifier"
    MATCHING_ENGINE_EVALUATE = "matching.engine_evaluate"
    MATCHING_MATCH_FAILED = "matching.match_failed"
    SYNC_PRE_PLAYLIST = "sync.pre_playlist"
    SYNC_POST_PLAYLIST = "sync.post_playlist"
    DOWNLOAD_PRE_QUEUE = "download.pre_queue"
    DOWNLOAD_POST_VERIFY = "download.post_verify"
    TAGGING_PRE_WRITE = "tagging.pre_write"
    TAGGING_POST_WRITE = "tagging.post_write"
    LIBRARY_REORGANIZE = "library.reorganize"
    WEBHOOK_RECEIVED = "webhook.received"


# The 7 active CJK language pack filter hooks + entity alias resolution hook,
# gated by `pipeline:enrich` or `pipeline:intercept` capabilities.
ACTIVE_PIPELINE_HOOK_CAPABILITIES: dict[str, str] = {
    "register_metadata_requirements": "pipeline:enrich",
    "post_metadata_enrichment": "pipeline:enrich",
    "resolve_entity_aliases": "pipeline:enrich",
    "pre_provider_search": "pipeline:intercept",
    "pre_normalize_text": "pipeline:intercept",
    "pre_normalize_title": "pipeline:intercept",
    "scoring_modifier": "pipeline:intercept",
    "search_expansion": "pipeline:intercept",
}

# The 16 retired unsubscribed hooks replaced by explicit PipelineContext stage tracking.
RETIRED_UNSUBSCRIBED_HOOK_STAGES: dict[str, str] = {
    "ON_SCORING_WEIGHTS_CALCULATE": PipelineStage.SCORING_WEIGHTS_CALCULATE.value,
    "ON_ENGINE_EVALUATE": PipelineStage.MATCHING_ENGINE_EVALUATE.value,
    "ON_MATCH_FAILED": PipelineStage.MATCHING_MATCH_FAILED.value,
    "ON_WEBHOOK_RECEIVED": PipelineStage.WEBHOOK_RECEIVED.value,
    "post_musicbrainz_fetch": PipelineStage.METADATA_EXTERNAL_FETCH.value,
    "pre_track_ingest": PipelineStage.INGEST_PRE_TRACK.value,
    "post_track_ingest": PipelineStage.INGEST_POST_TRACK.value,
    "pre_fingerprint_extract": PipelineStage.FINGERPRINT_PRE_EXTRACT.value,
    "post_fingerprint_extract": PipelineStage.FINGERPRINT_POST_EXTRACT.value,
    "pre_playlist_sync": PipelineStage.SYNC_PRE_PLAYLIST.value,
    "post_playlist_sync": PipelineStage.SYNC_POST_PLAYLIST.value,
    "pre_download_queue": PipelineStage.DOWNLOAD_PRE_QUEUE.value,
    "post_download_verify": PipelineStage.DOWNLOAD_POST_VERIFY.value,
    "pre_tag_write": PipelineStage.TAGGING_PRE_WRITE.value,
    "post_tag_write": PipelineStage.TAGGING_POST_WRITE.value,
    "on_library_reorganize": PipelineStage.LIBRARY_REORGANIZE.value,
}


@dataclass(frozen=True)
class StageRecord:
    """Immutable audit record of a single pipeline stage transition."""

    stage: str
    status: str = "completed"
    timestamp_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineContext:
    """Explicit stage-tracking context for ingestion, matching, enrichment, and sync pipelines."""

    context_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    pipeline_name: str = "default"
    entity_type: str = "track"
    entity_id: int | str | None = None
    current_stage: str | None = None
    stages: list[StageRecord] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)
    aborted: bool = False
    abort_reason: str | None = None

    def record_stage(
        self,
        stage: str | PipelineStage,
        status: str = "completed",
        duration_ms: float = 0.0,
        **metadata: Any,
    ) -> StageRecord:
        """Record a pipeline stage transition directly on the context."""
        stage_name = stage.value if isinstance(stage, PipelineStage) else str(stage)
        self.current_stage = stage_name
        record = StageRecord(
            stage=stage_name,
            status=status,
            duration_ms=float(duration_ms),
            metadata=dict(metadata),
        )
        self.stages.append(record)
        return record

    @contextlib.contextmanager
    def stage(self, stage: str | PipelineStage, **metadata: Any) -> Iterator[PipelineContext]:
        """Context manager measuring and recording execution of a pipeline stage."""
        stage_name = stage.value if isinstance(stage, PipelineStage) else str(stage)
        self.current_stage = stage_name
        start = time.perf_counter()
        status = "completed"
        try:
            yield self
        except Exception as exc:
            status = "failed"
            metadata = {**metadata, "error": str(exc)}
            raise
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            self.record_stage(stage_name, status=status, duration_ms=elapsed_ms, **metadata)

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def get_attribute(self, key: str, default: Any = None) -> Any:
        return self.attributes.get(key, default)

    def abort(self, reason: str) -> None:
        self.aborted = True
        self.abort_reason = reason

    @property
    def stage_names(self) -> list[str]:
        return [s.stage for s in self.stages]

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_id": self.context_id,
            "pipeline_name": self.pipeline_name,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "current_stage": self.current_stage,
            "stages": [
                {
                    "stage": s.stage,
                    "status": s.status,
                    "timestamp_ms": s.timestamp_ms,
                    "duration_ms": s.duration_ms,
                    "metadata": s.metadata,
                }
                for s in self.stages
            ],
            "attributes": dict(self.attributes),
            "metrics": dict(self.metrics),
            "aborted": self.aborted,
            "abort_reason": self.abort_reason,
        }


_current_pipeline_context: contextvars.ContextVar[PipelineContext | None] = contextvars.ContextVar(
    "echosync_current_pipeline_context",
    default=None,
)


def get_current_pipeline_context() -> PipelineContext | None:
    """Return the active PipelineContext bound to the current execution context, if any."""
    return _current_pipeline_context.get()


def set_current_pipeline_context(ctx: PipelineContext | None):
    """Bind a PipelineContext to the current contextvar and return its reset token."""
    return _current_pipeline_context.set(ctx)


@contextlib.contextmanager
def pipeline_context_scope(ctx: PipelineContext | None = None, **kwargs: Any) -> Iterator[PipelineContext]:
    """Context manager scoping an active PipelineContext cleanly."""
    active_ctx = ctx if ctx is not None else PipelineContext(**kwargs)
    token = _current_pipeline_context.set(active_ctx)
    try:
        yield active_ctx
    finally:
        _current_pipeline_context.reset(token)
