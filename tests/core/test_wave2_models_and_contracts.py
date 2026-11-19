"""Wave 2 unit tests: passive immutable domain DTOs, duration_ms, version_type, and re-exports."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from types import SimpleNamespace

import pytest

from core.db import echo_sync_track as legacy_module
from core.matching_engine.track_parser import normalize_track_dto
from core.models import (
    DISTINCT_VERSION_TYPES,
    SUBSTITUTABLE_VERSION_TYPES,
    ArtistCredit,
    DownloadStatus,
    EchosyncAlbum,
    EchosyncArtist,
    EchosyncMedia,
    EchosyncTrack,
    QualityTag,
    classify_version_type,
)


def test_domain_dtos_are_frozen_and_reexported():
    artist = EchosyncArtist(name="Daft Punk", sort_name="Daft Punk")
    album = EchosyncAlbum(title="Discovery", artist_name="Daft Punk", release_date="2001-01-01")
    media = EchosyncMedia(file_path="/music/discovery/01.flac", file_format="flac", duration_ms=320_000)
    credit = ArtistCredit(name="Daft Punk", role="primary", position=0)
    track = EchosyncTrack(
        title="One More Time",
        raw_title="One More Time",
        artist_name="Daft Punk",
        duration_ms=320_000,
        primary_artists=[artist],
        media=[media],
    )

    for obj, attr, val in (
        (credit, "name", "Other"),
        (artist, "name", "Other"),
        (album, "title", "Other"),
        (media, "duration_ms", 1000),
        (track, "title", "Other"),
    ):
        with pytest.raises(FrozenInstanceError):
            setattr(obj, attr, val)

    # Canonical re-exports from core.db.echo_sync_track preserve identity
    assert legacy_module.ArtistCredit is ArtistCredit
    assert legacy_module.EchosyncArtist is EchosyncArtist
    assert legacy_module.EchosyncAlbum is EchosyncAlbum
    assert legacy_module.EchosyncMedia is EchosyncMedia
    assert legacy_module.EchosyncTrack is EchosyncTrack
    assert legacy_module.SUBSTITUTABLE_VERSION_TYPES is SUBSTITUTABLE_VERSION_TYPES
    assert legacy_module.DISTINCT_VERSION_TYPES is DISTINCT_VERSION_TYPES
    assert legacy_module.DownloadStatus is DownloadStatus
    assert legacy_module.QualityTag is QualityTag
    assert legacy_module.classify_version_type is classify_version_type


def test_echosync_track_init_has_zero_side_effects_and_no_hook_execution(monkeypatch):
    from core.hook_manager import hook_manager

    hook_calls: list[tuple[str, tuple, dict]] = []

    def fail_if_called(hook_name: str, *args, **kwargs):
        hook_calls.append((hook_name, args, kwargs))
        raise AssertionError(f"Hook {hook_name} must not run inside EchosyncTrack.__init__")

    monkeypatch.setattr(hook_manager, "apply_filters", fail_if_called, raising=False)
    monkeypatch.setattr(hook_manager, "execute_hook", fail_if_called, raising=False)

    track = EchosyncTrack(
        title="Midnight City",
        raw_title="/tmp/music/M83/Hurry Up/01 - Midnight City (Radio Edit) (feat. Guest).flac",
        artist_name="M83 feat. Guest",
        duration_ms=243_000,
    )

    assert hook_calls == []
    assert track.title == "Midnight City"
    assert track.raw_title == "/tmp/music/M83/Hurry Up/01 - Midnight City (Radio Edit) (feat. Guest).flac"
    assert track.artist_name == "M83 feat. Guest"
    assert track.sync_id is None
    assert track.primary_artists == []
    assert track.featured_artists == []
    assert track.version_type == "original"


def test_duration_ms_canonical_and_legacy_float_duration_banned_on_constructor():
    with pytest.raises(TypeError):
        EchosyncTrack(title="Bad", duration=180.5)  # type: ignore[call-arg]

    # Legacy float seconds in dict payloads convert deterministically to int duration_ms
    converted = EchosyncTrack.from_dict(
        {
            "title": "Digital Love",
            "artist": "Daft Punk",
            "duration": 298.4,
            "edition": "Deluxe Edition",
        }
    )
    assert converted.duration_ms == 298_400
    assert converted.version_type == "deluxe"

    # Explicit duration_ms takes precedence over float seconds
    explicit = EchosyncTrack.from_dict(
        {
            "title": "Digital Love",
            "artist_name": "Daft Punk",
            "duration_ms": 298_000,
            "duration": 999.0,
        }
    )
    assert explicit.duration_ms == 298_000

    # Dict-style access helpers & to_dict compatibility remain functional and non-mutating
    assert converted.get("title") == "Digital Love"
    assert converted["duration_ms"] == 298_400
    assert "artist_name" in converted
    payload = converted.to_dict()
    assert payload["duration_ms"] == 298_400
    assert payload["version_type"] == "deluxe"


def test_version_type_taxonomy_constants_and_classifier():
    assert SUBSTITUTABLE_VERSION_TYPES == frozenset(
        {"original", "deluxe", "anniversary", "remaster", "soundtrack"}
    )
    assert DISTINCT_VERSION_TYPES == frozenset(
        {"remix", "acoustic", "instrumental", "live", "parody", "extended"}
    )
    assert SUBSTITUTABLE_VERSION_TYPES.isdisjoint(DISTINCT_VERSION_TYPES)

    assert classify_version_type(None, None) == "original"
    assert classify_version_type("2011 Remaster") == "remaster"
    assert classify_version_type("25th Anniversary Edition") == "anniversary"
    assert classify_version_type("Deluxe Version") == "deluxe"
    assert classify_version_type("Motion Picture Soundtrack") == "soundtrack"
    assert classify_version_type("Club Remix") == "remix"
    assert classify_version_type("Acoustic Session") == "acoustic"
    assert classify_version_type("Instrumental") == "instrumental"
    assert classify_version_type("Live at Wembley") == "live"
    assert classify_version_type("Extended Mix") == "extended"


def test_from_orm_and_explicit_normalize_track_dto(monkeypatch):
    from core.hook_manager import hook_manager

    hook_seen: list[str] = []

    def spy_apply_filters(hook_name: str, value: str, **_kwargs):
        hook_seen.append(hook_name)
        return value

    monkeypatch.setattr(hook_manager, "apply_filters", spy_apply_filters, raising=False)

    orm_track = SimpleNamespace(
        id=42,
        title="Around the World",
        artist=SimpleNamespace(id=7, name="Daft Punk", sort_name="Daft Punk", musicbrainz_id=None),
        album=SimpleNamespace(title="Homework", release_year=1997, album_type="album"),
        duration=429_000,
        musicbrainz_id="mbid-123",
        isrc="FRZ119600040",
        sync_id="sync-42",
        version_type="remaster",
        edition="2022 Remaster",
        track_number=7,
        disc_number=1,
        artist_associations=[],
        media_files=[],
    )

    from_orm_dto = EchosyncTrack.from_orm(orm_track)
    assert from_orm_dto.duration_ms == 429_000
    assert from_orm_dto.artist_name == "Daft Punk"
    assert from_orm_dto.version_type == "remaster"
    assert hook_seen == []

    # Explicit ingestion/parser normalization mutates nothing on input, invokes hook explicitly
    raw = EchosyncTrack(
        title="Midnight City (Club Remix) (feat. M83)",
        artist_name="Artist A",
        duration_ms=250_000,
    )
    normalized = normalize_track_dto(raw, generate_sync_id=True)
    assert "pre_normalize_title" in hook_seen
    assert raw.version_type == "original"
    assert raw.sync_id is None
    assert normalized.version_type == "remix"
    assert normalized.sync_id is not None
    assert replace(normalized, title="Midnight City").title == "Midnight City"
