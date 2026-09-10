"""Nexus Framework SDK - Core public interface for plugins and services."""

from __future__ import annotations

from pathlib import Path

from core.nexus_framework.plugin_SDK import *


def verify_file_signature(file_path: str | Path, title: str, artist: str) -> bool:
    """Verify the native cryptographic Content-Addressed Acoustic Proof (ECHOSYNC_SIGNATURE).

    Extracts the physical ECHOSYNC_SIGNATURE tag from the container, decodes the raw
    PCM stream, and verifies the BLAKE3 signature matches BLAKE3(pcm_hash:title:artist).
    Returns True if valid and untampered, False otherwise.
    """
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        return False

    try:
        import echosync_core

        raw_tags = echosync_core.extract_metadata(str(path)) or {}
        sig = (
            raw_tags.get("echosync_signature")
            or raw_tags.get("ECHOSYNC_SIGNATURE")
        )
        if not sig:
            return False

        return bool(
            echosync_core.verify_audio_signature(
                str(path), str(title).strip(), str(artist).strip(), str(sig).strip()
            )
        )
    except Exception:
        return False
