from enum import Enum, auto

class Capability(Enum):
    """
    Capabilities that a provider can support.
    Used for discovering providers that can perform specific tasks.
    """
    RESOLVE_FINGERPRINT = auto()  # Can resolve audio fingerprints (e.g., AcoustID)
    FETCH_METADATA = auto()       # Can fetch metadata (e.g., MusicBrainz)
    TAG_FILES = auto()            # Can write metadata tags to local audio files
    STREAM_AUDIO = auto()         # Can stream / play back audio locally
    SYNC_LIBRARY = auto()         # Can sync a full media-server library
