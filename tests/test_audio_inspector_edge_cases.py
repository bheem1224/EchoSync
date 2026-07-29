"""
tests/test_audio_inspector_edge_cases.py — Unit test suite for Dirty Six metadata edge cases.

Tests:
1. Encoding Sanitization (Bytes, Latin-1/CP1252 fallbacks, Mojibake repair).
2. Multi-Delimiter Artist Tokenization (;, ,, /, &, feat., ft., with).
3. Robust Year/Date Extraction (ISO formats, TYER, TDRC, messy strings).
4. Enhanced Track/Disc Integer Coercion (CD 1, Disc 2, Trk 05, 2/10, Track #03).
5. Malformed RIFF Container Tag Discard (RIFFINFO_*, raw chunk tokens).
6. Audio Inspector Integration via mock tag payloads.
"""

from pathlib import Path
from unittest.mock import patch
import pytest

from core.matching_engine.text_utils import (
    sanitize_string,
    parse_year_safe,
    split_artists,
    parse_int_safe,
)
from core.file_handling.audio_inspector import (
    inspect_audio_file,
    _is_corrupt_riff_tag,
    InspectedAudio,
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Encoding Sanitization
# ─────────────────────────────────────────────────────────────────────────────

def test_sanitize_string_clean_str():
    assert sanitize_string("Elton John") == "Elton John"
    assert sanitize_string("  Too Low for Zero  ") == "Too Low for Zero"


def test_sanitize_string_bytes_utf8():
    b_utf8 = "Björk".encode("utf-8")
    assert sanitize_string(b_utf8) == "Björk"


def test_sanitize_string_bytes_latin1():
    b_latin1 = "Café".encode("latin-1")
    assert sanitize_string(b_latin1) == "Café"


def test_sanitize_string_list_unpack():
    assert sanitize_string(["Queen", "Freddie Mercury"]) == "Queen"
    assert sanitize_string([]) is None


def test_sanitize_string_mojibake_repair():
    # "Café" encoded as UTF-8 then mis-decoded as Latin-1 yields "CafÃ©"
    mojibake = "CafÃ©"
    assert sanitize_string(mojibake) == "Café"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Multi-Delimiter Artist Tokenization
# ─────────────────────────────────────────────────────────────────────────────

def test_split_artists_single():
    assert split_artists("Elton John") == ["Elton John"]


def test_split_artists_delimiters():
    # Semicolon, comma, slash, ampersand, feat., ft., with
    res1 = split_artists("Queen; David Bowie")
    assert res1 == ["Queen", "David Bowie"]

    res2 = split_artists("Daft Punk / Pharrell Williams, Nile Rodgers")
    assert res2 == ["Daft Punk", "Pharrell Williams", "Nile Rodgers"]

    res3 = split_artists("Kanye West & Jay-Z feat. Frank Ocean")
    assert res3 == ["Kanye West", "Jay-Z", "Frank Ocean"]

    res4 = split_artists("Gorillaz ft. 2D with Del The Funky Homosapien")
    assert res4 == ["Gorillaz", "2D", "Del The Funky Homosapien"]


def test_split_artists_deduplication():
    res = split_artists("Artist A / Artist B & Artist A")
    assert res == ["Artist A", "Artist B"]


# ─────────────────────────────────────────────────────────────────────────────
# 3. Robust Year/Date Extraction
# ─────────────────────────────────────────────────────────────────────────────

def test_parse_year_safe_iso_and_messy():
    assert parse_year_safe("2021-05-14") == "2021"
    assert parse_year_safe("2004/01/01") == "2004"
    assert parse_year_safe("ISO 8601 1999") == "1999"
    assert parse_year_safe("TYER: 1985") == "1985"
    assert parse_year_safe(1973) == "1973"
    assert parse_year_safe(["1991-11-24"]) == "1991"


def test_parse_year_safe_invalid():
    assert parse_year_safe("No Year Here") is None
    assert parse_year_safe(None) is None
    assert parse_year_safe("") is None


# ─────────────────────────────────────────────────────────────────────────────
# 4. Enhanced Track/Disc Coercion
# ─────────────────────────────────────────────────────────────────────────────

def test_parse_int_safe_dirty_prefixes():
    assert parse_int_safe("2/10") == 2
    assert parse_int_safe("CD 1") == 1
    assert parse_int_safe("Disc 2") == 2
    assert parse_int_safe("Trk 05") == 5
    assert parse_int_safe("Track #03") == 3
    assert parse_int_safe("02-05") == 2


def test_parse_int_safe_data_types():
    assert parse_int_safe(7) == 7
    assert parse_int_safe(7.0) == 7
    assert parse_int_safe(["04/12"]) == 4
    assert parse_int_safe(None) is None
    assert parse_int_safe("Unknown") is None


# ─────────────────────────────────────────────────────────────────────────────
# 5. Malformed RIFF Container Tag Discard
# ─────────────────────────────────────────────────────────────────────────────

def test_is_corrupt_riff_tag():
    assert _is_corrupt_riff_tag("RIFFINFO_INAM") is True
    assert _is_corrupt_riff_tag("RIFFINFO_IART") is True
    assert _is_corrupt_riff_tag("INAM") is True
    assert _is_corrupt_riff_tag("IART") is True
    assert _is_corrupt_riff_tag("Elton John") is False
    assert _is_corrupt_riff_tag(None) is False


# ─────────────────────────────────────────────────────────────────────────────
# 6. Audio Inspector Integration via Mock Payload
# ─────────────────────────────────────────────────────────────────────────────

def test_inspect_audio_file_dirty_six_resilience(tmp_path):
    # Create a dummy test file path: .../Elton John/Too Low for Zero/02 - I'm Still Standing.flac
    artist_dir = tmp_path / "Elton John"
    album_dir = artist_dir / "Too Low for Zero"
    album_dir.mkdir(parents=True)
    file_path = album_dir / "02 - I'm Still Standing.flac"
    file_path.touch()

    dirty_tags = {
        "title": "RIFFINFO_INAM",  # Corrupt RIFF tag -> should fall back to file_path.stem
        "artist": b"Caf\xc3\xa9",     # Bytes UTF-8 -> "Café"
        "album_artist": "INAM",     # Corrupt raw token -> discarded
        "album": "Too Low for Zero",
        "date": "1983-05-30T00:00:00Z",  # Full ISO timestamp -> "1983"
        "track_number": "Trk 02/09",      # Prefix + slash -> 2
        "disc_number": "CD 1",            # Prefix -> 1
    }

    with patch("core.file_handling.tagging_io.read_tags", return_value=dirty_tags):
        result = inspect_audio_file(file_path)

        assert isinstance(result, InspectedAudio)
        assert result.title == "02 - I'm Still Standing"  # fell back to stem because title tag was RIFFINFO_INAM
        assert result.artist == "Café"                   # safely decoded bytes
        assert result.album == "Too Low for Zero"
        assert result.year == "1983"                     # extracted 4-digit year
        assert result.track_number == 2                  # cleaned "Trk 02/09"
        assert result.disc_number == 1                   # cleaned "CD 1"
