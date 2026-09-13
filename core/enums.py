from enum import Enum, auto


class Capability(Enum):
    """
    Capabilities that a provider can support.
    Used for discovering providers that can perform specific tasks.
    """

    RESOLVE_FINGERPRINT = auto()  # Can resolve audio fingerprints (e.g., AcoustID)
    FETCH_METADATA = auto()  # Can fetch metadata (e.g., MusicBrainz)
    TAG_FILES = auto()  # Can write metadata tags to local audio files
    STREAM_AUDIO = auto()  # Can stream / play back audio locally
    SYNC_LIBRARY = auto()  # Can sync a full media-server library
    FETCH_BY_ISRC = auto()  # Can resolve track metadata by ISRC code
    CLIENT_PREFILTER = auto()  # Supports client-side query post-filtering (includes/excludes/bounds)


class TaskCategory(str, Enum):
    GENERAL = "general"
    CRITICAL = "critical"
    DATABASE_WRITE_HEAVY = "database_write_heavy"
    BACKGROUND_METADATA = "background_metadata"


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    BLOCKED_WAITING_LEASE = "blocked_waiting_lease"
    PAUSED = "paused"
    RETRY_BACKOFF = "retry_backoff"
    COMPLETED = "completed"
    FAILED_TERMINAL = "failed_terminal"
    CANCELLED = "cancelled"

    # Legacy compatibility aliases
    IDLE = "queued"
    PENDING = "queued"
    PENDING_BLOCKED = "blocked_waiting_lease"
    FAILED = "failed_terminal"


class TaskPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
