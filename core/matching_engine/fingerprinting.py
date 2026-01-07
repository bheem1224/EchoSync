"""
Chromaprint Fingerprinting Module for SoulSync

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
        except ImportError:
            logger.warning(
                "pyacoustid not installed. Fingerprinting unavailable. "
                "Install with: pip install pyacoustid"
            )
            return None

        if not FingerprintGenerator.can_fingerprint(file_path):
            logger.warning(f"Cannot fingerprint {file_path}: unsupported format")
            return None

        try:
            # Generate fingerprint using Chromaprint
            # acoustid.fingerprint() returns (MBID, fingerprint)
            # We only need the fingerprint
            _, fingerprint = acoustid.fingerprint_file(file_path)
            return fingerprint
        except Exception as e:
            logger.warning(f"Failed to fingerprint {file_path}: {e}")
            return None


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
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fingerprint_cache (
                    file_path TEXT PRIMARY KEY,
                    fingerprint TEXT NOT NULL,
                    file_hash TEXT NOT NULL,
                    cached_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()
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
            conn = sqlite3.connect(self.db_path)
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
            conn.close()
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
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """
                INSERT OR REPLACE INTO fingerprint_cache (file_path, fingerprint, file_hash)
                VALUES (?, ?, ?)
                """,
                (str(file_path), fingerprint, file_hash or "")
            )
            conn.commit()
            conn.close()
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
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """
                DELETE FROM fingerprint_cache
                WHERE datetime(cached_at) < datetime('now', ? || ' days')
                """,
                (f'-{days}',)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to clear expired fingerprints: {e}")
