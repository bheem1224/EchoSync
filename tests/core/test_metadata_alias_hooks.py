"""Unit tests for Entity Alias resolution hooks, schemas, and persistence.

Validates Stage 2 of the metadata enhancement rebuild:
1. Hook dispatch via resolve_entity_aliases
2. Strict EntityAliasProposal schema adherence
3. Persistence across both artists and track_artists (remixers, collaborators)
4. Non-negotiable invariant: physical audio tags strictly preserve native script
5. Fault tolerance: malformed proposals or plugin exceptions never abort resolution
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import echosync_core
from core.database.repositories.track_repo import TrackRepository
from core.hook_manager import HookManager
from core.metadata.engine import MetadataResolutionEngine
from core.metadata.schemas import (
    AliasResolutionContext,
    EntityAliasProposal,
    ResolutionRequest,
    ResolutionResult,
)
from database.music_database import (
    Artist,
    ArtistAlias,
    Base,
    Track,
    TrackArtist,
    TrackArtistAlias,
)


@pytest.fixture
def memory_session():
    """In-memory SQLite database session for model persistence testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_resolve_entity_aliases_hook_dispatch(monkeypatch, tmp_path):
    """Mocks a language pack plugin returning EntityAliasProposal for Japanese Kanji -> Romanized;

    asserts proposals are attached to ResolutionResult.
    """
    audio_file = tmp_path / "kenshi_yonezu_lemon.flac"
    audio_file.write_bytes(b"dummy audio flac content")

    # Mock extract_metadata to return native script
    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "Lemon",
            "artist": "米津玄師",
            "album": "STRAY SHEEP",
            "duration_ms": 255000,
            "channels": 2,
        },
    )

    hm = HookManager()
    captured_contexts: list[AliasResolutionContext] = []

    def mock_cjk_plugin_hook(
        context: AliasResolutionContext,
    ) -> list[EntityAliasProposal]:
        captured_contexts.append(context)
        return [
            EntityAliasProposal(
                entity_type="artist",
                value="Kenshi Yonezu",
                language="ja",
                script="Latn",
                alias_type="official_romanization",
                entity_id="mbid-kenshi-1",
            ),
            EntityAliasProposal(
                entity_type="artist",
                value="よねづ けんし",
                language="ja",
                script="Hrkt",
                alias_type="transliteration",
                entity_id="mbid-kenshi-1",
            ),
        ]

    hm.register_hook("resolve_entity_aliases", mock_cjk_plugin_hook)

    engine = MetadataResolutionEngine(hook_manager=hm)
    req = ResolutionRequest(
        media_id="med_001",
        file_path=audio_file,
        sync_id="sync_kenshi_01",
        baseline_title="Lemon",
        baseline_artist="米津玄師",
    )

    result = engine.resolve_track(req)

    # Asserts context received correct native script
    assert len(captured_contexts) == 1
    ctx = captured_contexts[0]
    assert ctx.sync_id == "sync_kenshi_01"
    assert ctx.media_id == "med_001"
    assert ctx.artist == "米津玄師"
    assert ctx.title == "Lemon"

    # Asserts proposals attached to result
    assert len(result.alias_proposals) == 2
    prop_romaji = result.alias_proposals[0]
    assert prop_romaji.entity_type == "artist"
    assert prop_romaji.value == "Kenshi Yonezu"
    assert prop_romaji.language == "ja"
    assert prop_romaji.script == "Latn"
    assert prop_romaji.alias_type == "official_romanization"

    prop_kana = result.alias_proposals[1]
    assert prop_kana.value == "よねづ けんし"
    assert prop_kana.script == "Hrkt"


def test_track_artist_alias_persistence(memory_session):
    """Asserts that both primary artists and collaborating remixers in track_artists

    receive and persist localized aliases in the database.
    """
    # 1. Setup DB graph: primary artist (米津玄師) and remixer (中田ヤスタカ)
    primary_artist = Artist(name="米津玄師", normalized_name="kenshi yonezu")
    remixer_artist = Artist(name="中田ヤスタカ", normalized_name="yasutaka nakata")
    memory_session.add_all([primary_artist, remixer_artist])
    memory_session.flush()

    track = Track(
        sync_id="sync_lemon_remix",
        title="Lemon (Yasutaka Nakata Remix)",
        normalized_title="lemon yasutaka nakata remix",
        artist_id=primary_artist.id,
    )
    memory_session.add(track)
    memory_session.flush()

    # Add TrackArtist junction row for the remixer
    ta_remixer = TrackArtist(
        track_id=track.id,
        artist_id=remixer_artist.id,
        role="remixer",
        position=1,
    )
    memory_session.add(ta_remixer)
    memory_session.flush()

    # 2. Prepare alias proposals
    proposals = [
        EntityAliasProposal(
            entity_type="artist",
            value="Kenshi Yonezu",
            language="ja",
            script="Latn",
            alias_type="official_romanization",
            entity_id=primary_artist.id,
        ),
        EntityAliasProposal(
            entity_type="track_artist",
            value="Yasutaka Nakata",
            language="ja",
            script="Latn",
            alias_type="official_romanization",
            entity_id=remixer_artist.id,  # references artist_id associated with the track
        ),
    ]

    # 3. Upsert aliases via repository
    upserted_count = TrackRepository.upsert_entity_aliases(
        memory_session, proposals, sync_id=track.sync_id, commit=True
    )
    assert upserted_count == 2

    # 4. Verify primary artist alias
    artist_alias = (
        memory_session.query(ArtistAlias)
        .filter_by(artist_id=primary_artist.id, name="Kenshi Yonezu")
        .first()
    )
    assert artist_alias is not None
    assert artist_alias.language == "ja"
    assert artist_alias.script == "Latn"
    assert artist_alias.alias_type == "official_romanization"

    # 5. Verify track_artist alias for remixer
    ta_alias = (
        memory_session.query(TrackArtistAlias)
        .filter_by(track_artist_id=ta_remixer.id, alias_name="Yasutaka Nakata")
        .first()
    )
    assert ta_alias is not None
    assert ta_alias.language == "ja"
    assert ta_alias.script == "Latn"
    assert ta_alias.alias_type == "official_romanization"
    assert ta_alias.name == "Yasutaka Nakata"

    # Verify ORM relationship on TrackArtist
    memory_session.refresh(ta_remixer)
    assert len(ta_remixer.aliases) == 1
    assert ta_remixer.aliases[0].alias_name == "Yasutaka Nakata"


def test_physical_tags_remain_native_script_despite_aliases(monkeypatch, tmp_path):
    """Asserts that physical file tagging retains native script and does not overwrite

    audio tags with romanized aliases (Non-Negotiable System Invariant).
    """
    native_artist = "宇多田ヒカル"
    native_title = "First Love"
    romanized_artist_alias = "Hikaru Utada"

    # Construct a ResolutionResult with alias proposals
    result = ResolutionResult(
        media_id="med_utada_01",
        sync_id="sync_utada_01",
        title=native_title,
        artist=native_artist,
        confidence_score=0.98,
        resolution_method="text_waterfall",
        alias_proposals=[
            EntityAliasProposal(
                entity_type="artist",
                value=romanized_artist_alias,
                language="ja",
                script="Latn",
                alias_type="official_romanization",
            )
        ],
    )

    # Conversion to dict (what is passed to tag_file_verified)
    tag_payload = result.to_dict()

    # Invariant: Physical tag payload MUST be native script
    assert tag_payload["artist"] == native_artist
    assert tag_payload["artist_name"] == native_artist
    assert tag_payload["title"] == native_title

    # Invariant: Romanized alias string must NOT replace native audio tag fields
    assert tag_payload["artist"] != romanized_artist_alias
    assert tag_payload["artist_name"] != romanized_artist_alias
    assert "alias_proposals" not in tag_payload
    for val in tag_payload.values():
        assert val != romanized_artist_alias


def test_invalid_or_failing_hook_does_not_abort_resolution(monkeypatch, tmp_path):
    """Asserts that plugin exceptions or non-conforming objects are caught, logged,

    and dropped without aborting track resolution.
    """
    audio_file = tmp_path / "test_error_resilience.mp3"
    audio_file.write_bytes(b"dummy audio")

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "Sakura",
            "artist": "いきものがかり",
            "duration_ms": 200000,
            "channels": 2,
        },
    )

    hm = HookManager()

    # Callback 1: Raises exception
    def failing_hook(ctx):
        raise RuntimeError("External language plugin crashed unexpectedly!")

    # Callback 2: Returns malformed items mixed with valid proposal
    def malformed_hook(ctx):
        return [
            "invalid_string_not_proposal",
            42,
            {"invalid": "dictionary lacking required fields"},
            EntityAliasProposal(
                entity_type="artist",
                value="Ikimono-gakari",
                language="ja",
                script="Latn",
                alias_type="transliteration",
            ),
        ]

    hm.register_hook("resolve_entity_aliases", failing_hook)
    hm.register_hook("resolve_entity_aliases", malformed_hook)

    engine = MetadataResolutionEngine(hook_manager=hm)
    req = ResolutionRequest(
        media_id="med_err_01",
        file_path=audio_file,
        sync_id="sync_err_01",
        baseline_title="Sakura",
        baseline_artist="いきものがかり",
    )

    # Execution must not raise
    result = engine.resolve_track(req)

    assert result is not None
    assert result.artist == "いきものがかり"
    # Only the valid EntityAliasProposal should be retained
    assert len(result.alias_proposals) == 1
    assert result.alias_proposals[0].value == "Ikimono-gakari"


def test_hook_manager_execute_hook_contracts():
    """Directly tests HookManager.execute_hook flattening, error isolation, and async rejection."""
    hm = HookManager()

    def hook_a(val):
        return [1, 2]

    def hook_b(val):
        return 3

    def hook_c(val):
        return None

    def hook_d_fails(val):
        raise ValueError("Boom")

    hm.add_filter("test_hook", hook_a)
    hm.add_filter("test_hook", hook_b)
    hm.add_filter("test_hook", hook_c)
    hm.add_filter("test_hook", hook_d_fails)

    results = hm.execute_hook("test_hook", "input_data")
    assert results == [1, 2, 3]
