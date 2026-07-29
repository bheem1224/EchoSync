"""
Standalone Diagnostic Tool for EchoSync Local Library Scanner.

Dry-runs directory scanning on a target path, printing skipped files,
validation issues, raw exception stack traces, and tag coercion errors.

Usage:
    python -m tools.scan_diagnostics --path "/path/to/music/folder"
"""

import argparse
import os
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional


def parse_int_safe(val: Any) -> Optional[int]:
    """Parse integer safely from strings like '2/9', '02', tuples, or floats."""
    if val is None or val == "":
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return int(val)
    if isinstance(val, (list, tuple)):
        if len(val) > 0:
            return parse_int_safe(val[0])
        return None
    s = str(val).strip()
    if not s:
        return None
    if "/" in s:
        s = s.split("/", 1)[0].strip()
    try:
        return int(s)
    except (ValueError, TypeError):
        return None


def run_diagnostics(target_dir: Path) -> None:
    print(f"=== EchoSync Scanner Diagnostic Run ===")
    print(f"Target Directory: {target_dir.resolve()}\n")

    if not target_dir.exists():
        print(f"ERROR: Directory '{target_dir}' does not exist.")
        sys.exit(1)

    supported_exts = {
        '.mp3', '.flac', '.ogg', '.m4a', '.aac',
        '.alac', '.ape', '.wav', '.dsd', '.dsf', '.dff'
    }

    # Import core tagging and model dependencies
    try:
        from core.file_handling.tagging_io import read_tags
        from core.nexus_framework.plugin_SDK import PluginBase
    except ImportError as ie:
        print(f"ERROR: Failed to import EchoSync core modules: {ie}")
        sys.exit(1)

    total_files = 0
    valid_files = 0
    skipped_files: List[Dict[str, Any]] = []

    for root, dirs, files in os.walk(target_dir):
        for file in files:
            path = Path(root) / file
            if path.suffix.lower() not in supported_exts:
                continue

            total_files += 1
            file_issues = []
            exc_traceback = None
            tags = {}

            # 1. Tag Reading Check
            try:
                tags = read_tags(path)
            except Exception as exc:
                file_issues.append(f"Tag Extraction Exception: {exc}")
                exc_traceback = traceback.format_exc()

            # 2. Extract Metadata Fields
            title = tags.get('title') or path.stem
            _tag_artist = (tags.get('artist') or '').strip()
            _album_artist = (tags.get('album_artist') or '').strip()
            _VA_TERMS = {'various artists', 'various', 'va'}

            if _tag_artist and _tag_artist.lower() not in _VA_TERMS:
                artist = _tag_artist
            elif _album_artist and _album_artist.lower() not in _VA_TERMS:
                artist = _album_artist
            elif _tag_artist:
                artist = _tag_artist
            else:
                artist = ""

            # 3. Artist Missing Warning
            if not artist:
                file_issues.append("Missing Artist Tag: Neither TPE1 (artist) nor TPE2 (album_artist) present")

            # 4. Check Track/Disc Number Formatting
            raw_track_num = tags.get('track_number') or tags.get('tracknumber')
            parsed_track_num = parse_int_safe(raw_track_num)
            if raw_track_num is not None and parsed_track_num is None:
                file_issues.append(f"Invalid Track Number format: '{raw_track_num}' (could not coerce to int)")

            raw_disc_num = tags.get('disc_number') or tags.get('discnumber')
            parsed_disc_num = parse_int_safe(raw_disc_num)
            if raw_disc_num is not None and parsed_disc_num is None:
                file_issues.append(f"Invalid Disc Number format: '{raw_disc_num}' (could not coerce to int)")

            # 5. Test Track Object Instantiation
            track_obj = None
            try:
                track_obj = PluginBase.create_echo_sync_track(
                    title=title,
                    artist=artist or "Unknown Artist",
                    album=tags.get('album') or "",
                    duration_ms=tags.get('duration'),
                    track_number=parsed_track_num,
                    disc_number=parsed_disc_num,
                    file_path=str(path),
                    source="EchoSync.local_server"
                )
                if track_obj is None:
                    file_issues.append("create_echo_sync_track returned None (failed factory validation)")
            except Exception as exc:
                file_issues.append(f"EchosyncTrack Creation Exception: {exc}")
                exc_traceback = traceback.format_exc()

            if file_issues:
                skipped_files.append({
                    "path": str(path),
                    "issues": file_issues,
                    "traceback": exc_traceback
                })
            else:
                valid_files += 1

    # Print Summary Report
    print(f"=== Diagnostic Summary ===")
    print(f"Total Audio Files Found : {total_files}")
    print(f"Valid Processable Tracks : {valid_files}")
    print(f"Skipped / Problematic   : {len(skipped_files)}")
    print("-" * 50)

    if skipped_files:
        print("\n=== Skipped File Details ===")
        for idx, item in enumerate(skipped_files, 1):
            print(f"\n[{idx}] File: {item['path']}")
            for issue in item['issues']:
                print(f"    - Issue: {issue}")
            if item['traceback']:
                print(f"    - Traceback:\n{item['traceback']}")

    print("\nDiagnostic complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EchoSync Scanner Diagnostic Utility")
    parser.add_argument("--path", required=True, type=str, help="Target directory path to scan")
    args = parser.parse_args()
    run_diagnostics(Path(args.path))
