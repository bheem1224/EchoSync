"""
Chromaprint Fingerprinting Module for Echosync

Handles audio fingerprint generation and comparison for high-accuracy track matching.
Uses Chromaprint via pyacoustid to generate and compare fingerprints.

Fingerprints are useful for:
1. Identifying the same song across different quality/version/release versions
2. Detecting when file tags are completely wrong but the audio is correct
3. Library import where filename/tags are unreliable but audio is the truth
"""

import logging
from typing import Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class FingerprintGenerator:
    """Generate Chromaprint fingerprints from audio files"""

    SUPPORTED_FORMATS = {
        '.mp3', '.flac', '.m4a', '.aac', '.ogg', '.opus',
        '.wma', '.wav', '.alac', '.ape'
    }

    @staticmethod
    def can_fingerprint(file_path: str) -> bool:
        """Check if file can be fingerprinted"""
        path = Path(file_path)
        return path.suffix.lower() in FingerprintGenerator.SUPPORTED_FORMATS

    @staticmethod
    def _get_channel_count(file_path: str) -> Optional[int]:
        """Return the channel count for an audio file using mutagen, or None on failure."""
        try:
            suffix = Path(file_path).suffix.lower()
            if suffix == '.flac':
                from mutagen.flac import FLAC
                return FLAC(file_path).info.channels
            elif suffix == '.mp3':
                from mutagen.mp3 import MP3
                return MP3(file_path).info.channels
            elif suffix in ('.m4a', '.aac', '.alac'):
                from mutagen.mp4 import MP4
                return MP4(file_path).info.channels
            elif suffix == '.ogg':
                from mutagen.oggvorbis import OggVorbis
                return OggVorbis(file_path).info.channels
            elif suffix == '.opus':
                from mutagen.oggopus import OggOpus
                return OggOpus(file_path).info.channels
            elif suffix == '.wma':
                from mutagen.asf import ASF
                return ASF(file_path).info.channels
            elif suffix == '.wav':
                from mutagen.wave import WAVE
                return WAVE(file_path).info.channels
            # .ape and any unknown formats: skip the check
            return None
        except Exception as e:
            logger.debug("Could not probe channel count for %s: %s", file_path, e)
            return None

    @staticmethod
    def generate(file_path: str) -> Optional[str]:
        """
        Generate Chromaprint fingerprint from audio file

        Args:
            file_path: Path to audio file

        Returns:
            Chromaprint fingerprint string, or None if generation fails
        """
        try:
            import acoustid
            import os
        except ImportError:
            logger.warning(
                "pyacoustid not installed. Fingerprinting unavailable. "
                "Install with: pip install pyacoustid"
            )
            return None

        if not FingerprintGenerator.can_fingerprint(file_path):
            logger.warning(f"Cannot fingerprint {file_path}: unsupported format")
            return None

        channels = FingerprintGenerator._get_channel_count(file_path)
        if channels is not None and channels > 2:
            logger.warning(
                "Skipping AcoustID fingerprinting for multi-channel audio "
                "(>2 channels) to prevent C-library segfaults: %s (%d ch)",
                file_path, channels,
            )
            return None

        try:
            # Check if fpcalc is available
            fpcalc_path = os.environ.get('FPCALC', 'fpcalc')
            
            # Generate fingerprint using Chromaprint
            # acoustid.fingerprint_file() returns (duration, fingerprint)
            duration, fingerprint = acoustid.fingerprint_file(file_path)

            if isinstance(fingerprint, bytes):
                fingerprint = fingerprint.decode("utf-8", errors="ignore")
            
            if not fingerprint:
                logger.warning(f"Empty fingerprint generated for {file_path}")
                return None
            
            logger.debug(f"Generated fingerprint for {file_path}: length={len(fingerprint)}, duration={duration}s")
            return fingerprint
            
        except FileNotFoundError as e:
            logger.error(
                f"fpcalc command not found. Install Chromaprint and add fpcalc to PATH, "
                f"or set FPCALC environment variable. Error: {e}"
            )
            return None
        except Exception as e:
            logger.warning(f"Failed to fingerprint {file_path}: {e}")
            return None

    @staticmethod
    def generate_with_duration(file_path: str) -> Tuple[Optional[str], Optional[int]]:
        """Generate a Chromaprint fingerprint and return it together with the
        fpcalc-computed duration (in whole seconds).

        Using this avoids a second mutagen decode when both values are needed,
        which is especially important for WAV files where mutagen duration
        detection can be unreliable.

        Returns:
            ``(fingerprint, duration_seconds)`` — either value may be None on failure.
        """
        try:
            import acoustid
        except ImportError:
            logger.warning(
                "pyacoustid not installed. Fingerprinting unavailable. "
                "Install with: pip install pyacoustid"
            )
            return None, None

        if not FingerprintGenerator.can_fingerprint(file_path):
            logger.warning(f"Cannot fingerprint {file_path}: unsupported format")
            return None, None

        channels = FingerprintGenerator._get_channel_count(file_path)
        if channels is not None and channels > 2:
            logger.warning(
                "Skipping AcoustID fingerprinting for multi-channel audio "
                "(>2 channels) to prevent C-library segfaults: %s (%d ch)",
                file_path, channels,
            )
            return None, None

        try:
            raw_duration, fingerprint = acoustid.fingerprint_file(file_path)

            if isinstance(fingerprint, bytes):
                fingerprint = fingerprint.decode("utf-8", errors="ignore")

            if not fingerprint:
                logger.warning(f"Empty fingerprint generated for {file_path}")
                return None, None
            duration_sec = int(raw_duration) if raw_duration else None
            logger.debug(
                f"Generated fingerprint for {file_path}: "
                f"length={len(fingerprint)}, duration={duration_sec}s"
            )
            return fingerprint, duration_sec
        except FileNotFoundError as e:
            logger.error(
                f"fpcalc command not found. Install Chromaprint and add fpcalc to PATH, "
                f"or set FPCALC environment variable. Error: {e}"
            )
            return None, None
        except Exception as e:
            logger.warning(f"Failed to fingerprint {file_path}: {e}")
            return None, None


class FingerprintMatcher:
    """Compare fingerprints to detect identical/similar audio"""

    # Minimum confidence for fingerprint to be considered reliable (0-1)
    # Chromaprint confidence is the number of matching bits in fingerprint
    MIN_CONFIDENCE = 0.85

    @staticmethod
    def fingerprints_match(
        fp1: Optional[str],
        fp2: Optional[str],
        confidence_threshold: float = MIN_CONFIDENCE
    ) -> bool:
        """
        Compare two Chromaprint fingerprints

        Args:
            fp1: First fingerprint (or None)
            fp2: Second fingerprint (or None)
            confidence_threshold: Minimum confidence (0-1) to consider match

        Returns:
            True if fingerprints match with sufficient confidence
        """
        if not fp1 or not fp2:
            return False

        try:
            import acoustid
        except ImportError:
            return False

        try:
            # Compare fingerprints using acoustid library
            # This uses the AcousticID API or local comparison
            score = acoustid.compare(fp1, fp2)
            return score >= confidence_threshold
        except Exception as e:
            logger.debug(f"Fingerprint comparison failed: {e}")
            return False

    @staticmethod
    def get_confidence_score(fp1: Optional[str], fp2: Optional[str]) -> float:
        """
        Get confidence score for fingerprint match (0-1)

        Args:
            fp1: First fingerprint (or None)
            fp2: Second fingerprint (or None)

        Returns:
            Confidence score (0-1), or 0 if comparison fails
        """
        if not fp1 or not fp2:
            return 0.0

        try:
            import acoustid
        except ImportError:
            return 0.0

        try:
            score = acoustid.compare(fp1, fp2)
            return max(0.0, min(1.0, score))  # Clamp to 0-1
        except Exception as e:
            logger.debug(f"Fingerprint confidence calculation failed: {e}")
            return 0.0


class FingerprintCache:
    """Cache fingerprints to avoid regenerating them"""

    def __init__(self, database_path: str):
        """
        Initialize fingerprint cache

        Args:
            database_path: Path to SQLite database for caching
        """
        self.db_path = database_path
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """Ensure fingerprint cache table exists in database"""
        try:
            import sqlite3
            import contextlib
            with contextlib.closing(sqlite3.connect(self.db_path, timeout=30.0)) as conn:
                conn.execute("PRAGMA busy_timeout = 5000")
                conn.execute("PRAGMA journal_mode = WAL")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS fingerprint_cache (
                        file_path TEXT PRIMARY KEY,
                        fingerprint TEXT NOT NULL,
                        file_hash TEXT NOT NULL,
                        cached_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.warning(f"Failed to create fingerprint cache table: {e}")

    def get(self, file_path: str, file_hash: Optional[str] = None) -> Optional[str]:
        """
        Get cached fingerprint

        Args:
            file_path: Path to audio file
            file_hash: Optional file hash to validate cache freshness

        Returns:
            Cached fingerprint, or None if not cached or invalid
        """
        try:
            import sqlite3
            import contextlib
            with contextlib.closing(sqlite3.connect(self.db_path, timeout=30.0)) as conn:
                conn.execute("PRAGMA busy_timeout = 5000")
                conn.execute("PRAGMA journal_mode = WAL")
                cursor = conn.cursor()

                if file_hash:
                    cursor.execute(
                        "SELECT fingerprint FROM fingerprint_cache WHERE file_path = ? AND file_hash = ?",
                        (str(file_path), file_hash)
                    )
                else:
                    cursor.execute(
                        "SELECT fingerprint FROM fingerprint_cache WHERE file_path = ?",
                        (str(file_path),)
                    )

                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.debug(f"Failed to retrieve cached fingerprint: {e}")
            return None

    def set(self, file_path: str, fingerprint: str, file_hash: Optional[str] = None):
        """
        Cache a fingerprint

        Args:
            file_path: Path to audio file
            fingerprint: Generated fingerprint
            file_hash: Optional file hash for validation
        """
        try:
            import sqlite3
            import contextlib
            with contextlib.closing(sqlite3.connect(self.db_path, timeout=30.0)) as conn:
                conn.execute("PRAGMA busy_timeout = 5000")
                conn.execute("PRAGMA journal_mode = WAL")
                conn.execute(
                    """
                    INSERT OR REPLACE INTO fingerprint_cache (file_path, fingerprint, file_hash)
                    VALUES (?, ?, ?)
                    """,
                    (str(file_path), fingerprint, file_hash or "")
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"Failed to cache fingerprint: {e}")

    def clear_expired(self, days: int = 30):
        """
        Clear fingerprints older than specified days

        Args:
            days: Age threshold in days
        """
        try:
            import sqlite3
            import contextlib
            with contextlib.closing(sqlite3.connect(self.db_path, timeout=30.0)) as conn:
                conn.execute("PRAGMA busy_timeout = 5000")
                conn.execute("PRAGMA journal_mode = WAL")
                conn.execute(
                    """
                    DELETE FROM fingerprint_cache
                    WHERE datetime(cached_at) < datetime('now', ? || ' days')
                    """,
                    (f'-{days}',)
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"Failed to clear expired fingerprints: {e}")
