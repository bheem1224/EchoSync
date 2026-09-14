from unittest.mock import MagicMock
from pathlib import Path

import pytest
import echosync_core

from core.enums import Capability
from core.matching_engine.fingerprinting import FingerprintGenerator
from core.nexus_framework.plugin_loader import PluginRegistry
from database.music_database import (
    Album,
    Artist,
    Base,
    LocalMedia,
    MusicDatabase,
    Track,
)
from database.working_database import (
    SuggestionStagingQueue,
    WorkingBase,
    WorkingDatabase,
)
from services.metadata_enhancer import RetroactiveEnhancer


@pytest.fixture
def test_environment(tmp_path, monkeypatch):
    """Sets up isolated MusicDatabase and WorkingDatabase environments with monkeypatched get_database."""
    music_db = MusicDatabase(tmp_path / "music.db")
    Base.metadata.create_all(music_db.engine)

    working_db = WorkingDatabase(tmp_path / "working.db")
    WorkingBase.metadata.create_all(working_db.engine)

    monkeypatch.setattr("database.music_database.get_database", lambda: music_db)
    monkeypatch.setattr("database.get_database", lambda: music_db)
    monkeypatch.setattr("database.working_database.get_working_database", lambda: working_db)

    # Mock file-tag writer so physical audio files are not required to support mutagens
    written_tags = []
    monkeypatch.setattr(
        "services.metadata_enhancer._tagging_write",
        lambda p, tags: written_tags.append((Path(p), tags)),
    )

    return {
        "music_db": music_db,
        "working_db": working_db,
        "written_tags": written_tags,
        "tmp_path": tmp_path,
    }


def test_targeted_fetch_trust_gate_rejection_demotes_to_acoustic_waterfall(test_environment, monkeypatch):
    """When Targeted Fetch rejects an unsigned candidate title via trust gate,

    the track must be demoted to bucket_heavy and resolved via Chromaprint/AcoustID.
    """
    music_db = test_environment["music_db"]
    tmp_path = test_environment["tmp_path"]

    audio_file = tmp_path / "05 - My First Guitar.flac"
    audio_file.write_bytes(b"dummy bon jovi audio stream")

    file_dur_ms = 215000  # 215.0s

    with music_db.session_scope() as session:
        artist = Artist(name="Bon Jovi", normalized_name="bon jovi")
        # Album is unknown so is_bad_metadata is True, causing track with MBID to enter bucket_target
        album = Album(title="Unknown Album", normalized_title="unknown album", artist=artist)
        session.add_all([artist, album])
        session.flush()

        track = Track(
            title="My First Guitar (5)",
            normalized_title="my first guitar (5)",
            sync_id="sync_bon_jovi_2693",
            musicbrainz_id="mbid-wrong-target",  # Stored MBID that points to mismatched song
            artist=artist,
            album=album,
            duration=file_dur_ms,
        )
        session.add(track)
        session.flush()

        media = LocalMedia(
            track_id=track.id,
            file_path=str(audio_file),
            file_format="flac",
            media_id="media_2693",
        )
        session.add(media)

    # 1. Physical metadata extractor returns baseline tags
    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "My First Guitar (5)",
            "artist": "Bon Jovi",
            "album": "Unknown Album",
            "musicbrainz_id": "mbid-wrong-target",
            "duration_ms": file_dur_ms,
            "channels": 2,
        },
    )

    # 2. Fingerprint generator returns valid acoustic waveform
    dummy_chromaprint = "C" * 64
    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: (dummy_chromaprint, file_dur_ms / 1000.0),
    )

    # 3. Mock MusicBrainz plugin:
    #    - Returns divergent track "I Wrote You a Song" for "mbid-wrong-target"
    #    - Returns canonical metadata for acoustic winner "mbid-correct-acoustic"
    mock_mb = MagicMock()
    mock_mb.capabilities = type("Caps", (), {"supports_batching": False})()

    def mock_mb_get(mbid):
        if mbid == "mbid-wrong-target":
            return {
                "title": "I Wrote You a Song",
                "artist": "Bon Jovi",
                "album": "Forever",
                "year": 2024,
            }
        elif mbid == "mbid-correct-acoustic":
            return {
                "title": "My First Guitar",
                "artist": "Bon Jovi",
                "album": "Forever",
                "year": 2024,
                "release_id": "rel-bonjovi-forever",
                "isrc": "USUM72401234",
            }
        return None

    mock_mb.get_metadata.side_effect = mock_mb_get

    # 4. Mock AcoustID plugin: resolves dummy chromaprint to canonical recording
    mock_acoustid = MagicMock()
    mock_acoustid.capabilities = type(
        "Caps",
        (),
        {"fingerprint_algorithms": ["chromaprint"], "supports_fingerprinting": True},
    )()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "acoustid-bonjovi-2693",
        "score": 0.98,
        "recordings": [
            {
                "id": "mbid-correct-acoustic",
                "title": "My First Guitar",
                "artist": "Bon Jovi",
                "duration": file_dur_ms / 1000.0,
                "score": 0.98,
            }
        ],
        "mbids": ["mbid-correct-acoustic"],
    }

    def plugin_resolver(name):
        if name in (1990722619, "EchoSync.musicbrainz", "musicbrainz") or "musicbrainz" in str(name).lower():
            return mock_mb
        if name in (3801077393, "EchoSync.acoustid", "acoustid") or "acoustid" in str(name).lower():
            return mock_acoustid
        return None

    monkeypatch.setattr(PluginRegistry, "get_plugin", plugin_resolver)
    monkeypatch.setattr(
        PluginRegistry,
        "get_plugins_with_capability",
        lambda cap: (
            [mock_acoustid]
            if cap == Capability.RESOLVE_FINGERPRINT
            else ([mock_mb] if cap == Capability.FETCH_METADATA else [])
        ),
    )

    enhancer = RetroactiveEnhancer()
    enhancer.enhance_library_metadata(batch_size=1, limit=1, check_all_files=False)

    # Invariants:
    # 1. Track was NOT abandoned or left with 'NOT_FOUND'
    # 2. Track was demoted to bucket_heavy and successfully resolved via AcoustID
    with music_db.session_scope() as session:
        t = session.query(Track).filter_by(sync_id="sync_bon_jovi_2693").first()
        assert t is not None
        assert t.musicbrainz_id == "mbid-correct-acoustic"
        assert t.title == "My First Guitar"
        assert t.album.title == "Forever"
        assert t.metadata_status.get("enhanced") is True
        assert t.isrc == "USUM72401234"


def test_targeted_fetch_empty_data_demotes_to_acoustic_waterfall(test_environment, monkeypatch):
    """When Targeted Fetch returns no metadata (None or empty), unsigned track

    must be demoted to bucket_heavy and resolved via Chromaprint/AcoustID.
    """
    music_db = test_environment["music_db"]
    tmp_path = test_environment["tmp_path"]

    audio_file = tmp_path / "01 - Radioactive.mp3"
    audio_file.write_bytes(b"dummy imagine dragons audio stream")

    file_dur_ms = 186000

    with music_db.session_scope() as session:
        artist = Artist(name="Imagine Dragons", normalized_name="imagine dragons")
        # Unknown Album makes is_bad_metadata True
        album = Album(title="Unknown Album", normalized_title="unknown album", artist=artist)
        session.add_all([artist, album])
        session.flush()

        track = Track(
            title="Radioactive",
            normalized_title="radioactive",
            sync_id="sync_id_radioactive",
            musicbrainz_id="mbid-dead-end-empty",
            artist=artist,
            album=album,
            duration=file_dur_ms,
        )
        session.add(track)
        session.flush()

        media = LocalMedia(
            track_id=track.id,
            file_path=str(audio_file),
            file_format="mp3",
            media_id="media_radioactive_01",
        )
        session.add(media)

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "Radioactive",
            "artist": "Imagine Dragons",
            "album": "Unknown Album",
            "musicbrainz_id": "mbid-dead-end-empty",
            "duration_ms": file_dur_ms,
            "channels": 2,
        },
    )

    dummy_chromaprint = "D" * 64
    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: (dummy_chromaprint, file_dur_ms / 1000.0),
    )

    mock_mb = MagicMock()
    mock_mb.capabilities = type("Caps", (), {"supports_batching": False})()

    def mock_mb_get(mbid):
        if mbid == "mbid-dead-end-empty":
            return None  # MBID fetch returns nothing
        elif mbid == "mbid-radioactive-winner":
            return {
                "title": "Radioactive",
                "artist": "Imagine Dragons",
                "album": "Night Visions",
                "year": 2012,
                "release_id": "rel-night-visions",
            }
        return None

    mock_mb.get_metadata.side_effect = mock_mb_get

    mock_acoustid = MagicMock()
    mock_acoustid.capabilities = type(
        "Caps",
        (),
        {"fingerprint_algorithms": ["chromaprint"], "supports_fingerprinting": True},
    )()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "acoustid-radioactive-correct",
        "score": 0.99,
        "recordings": [
            {
                "id": "mbid-radioactive-winner",
                "title": "Radioactive",
                "artist": "Imagine Dragons",
                "duration": file_dur_ms / 1000.0,
                "score": 0.99,
            }
        ],
        "mbids": ["mbid-radioactive-winner"],
    }

    def plugin_resolver(name):
        if name in (1990722619, "EchoSync.musicbrainz", "musicbrainz") or "musicbrainz" in str(name).lower():
            return mock_mb
        if name in (3801077393, "EchoSync.acoustid", "acoustid") or "acoustid" in str(name).lower():
            return mock_acoustid
        return None

    monkeypatch.setattr(PluginRegistry, "get_plugin", plugin_resolver)
    monkeypatch.setattr(
        PluginRegistry,
        "get_plugins_with_capability",
        lambda cap: (
            [mock_acoustid]
            if cap == Capability.RESOLVE_FINGERPRINT
            else ([mock_mb] if cap == Capability.FETCH_METADATA else [])
        ),
    )

    enhancer = RetroactiveEnhancer()
    enhancer.enhance_library_metadata(batch_size=1, limit=1, check_all_files=False)

    with music_db.session_scope() as session:
        t = session.query(Track).filter_by(sync_id="sync_id_radioactive").first()
        assert t is not None
        assert t.musicbrainz_id == "mbid-radioactive-winner"
        assert t.album.title == "Night Visions"
        assert t.metadata_status.get("enhanced") is True


def test_targeted_fetch_signed_track_does_not_clobber(test_environment, monkeypatch):
    """Tracks with verified ECHOSYNC_SIGNATURE preserve tags, stage a review task on divergence,

    and are NOT automatically demoted or clobbered.
    """
    music_db = test_environment["music_db"]
    working_db = test_environment["working_db"]
    tmp_path = test_environment["tmp_path"]

    audio_file = tmp_path / "01 - Curated Song.flac"
    audio_file.write_bytes(b"dummy curated audio stream")

    with music_db.session_scope() as session:
        artist = Artist(name="Curated Artist", normalized_name="curated artist")
        album = Album(title="Unknown Album", normalized_title="unknown album", artist=artist)
        session.add_all([artist, album])
        session.flush()

        track = Track(
            title="Curated Title",
            normalized_title="curated title",
            sync_id="sync_curated_track",
            musicbrainz_id="mbid-signed-stale",
            artist=artist,
            album=album,
            echosync_signature="SIG_VALID_CURATED_123",
            metadata_status={"echosync_signature": "SIG_VALID_CURATED_123"},
        )
        session.add(track)
        session.flush()

        media = LocalMedia(
            track_id=track.id,
            file_path=str(audio_file),
            file_format="flac",
            media_id="media_curated_01",
        )
        session.add(media)

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "Curated Title",
            "artist": "Curated Artist",
            "album": "Unknown Album",
            "musicbrainz_id": "mbid-signed-stale",
            "echosync_signature": "SIG_VALID_CURATED_123",
            "channels": 2,
        },
    )
    monkeypatch.setattr(
        echosync_core,
        "verify_audio_signature",
        lambda path, title, artist, sig: True,
    )

    mock_mb = MagicMock()
    mock_mb.capabilities = type("Caps", (), {"supports_batching": False})()
    mock_mb.get_metadata.return_value = {
        "title": "Completely Different Title",
        "artist": "Curated Artist",
        "album": "Different Album",
        "year": 2020,
    }

    monkeypatch.setattr(PluginRegistry, "get_plugin", lambda name: mock_mb)

    enhancer = RetroactiveEnhancer()
    enhancer.enhance_library_metadata(batch_size=1, limit=1, check_all_files=False)

    # Invariants:
    # 1. File tags were NOT overwritten with divergent title
    # 2. Track title was NOT altered to 'Completely Different Title'
    # 3. SuggestionStagingQueue contains review item for the divergence
    with music_db.session_scope() as session:
        t = session.query(Track).filter_by(sync_id="sync_curated_track").first()
        assert t.title == "Curated Title"
        assert t.title != "Completely Different Title"

    with working_db.session_scope() as session:
        staged = session.query(SuggestionStagingQueue).all()
        assert len(staged) >= 1
        assert "Title similarity failed trust gate" in staged[0].context_data["divergence_reason"]
        assert staged[0].reason == "METADATA_DIVERGENCE"


def test_targeted_fetch_tampered_signature_voids_and_demotes_to_acoustic_waterfall(test_environment, monkeypatch):
    """Tracks with invalid/corrupted ECHOSYNC_SIGNATURE void the signature, demote to acoustic waterfall,

    and auto-apply canonical AcoustID tags without ReviewTask staging.
    """
    music_db = test_environment["music_db"]
    working_db = test_environment["working_db"]
    tmp_path = test_environment["tmp_path"]

    audio_file = tmp_path / "07 - My First Guitar (13).flac"
    audio_file.write_bytes(b"dummy corrupted signature audio stream")

    file_dur_ms = 220000

    with music_db.session_scope() as session:
        artist = Artist(name="Bon Jovi", normalized_name="bon jovi")
        album = Album(title="Unknown Album", normalized_title="unknown album", artist=artist)
        session.add_all([artist, album])
        session.flush()

        track = Track(
            title="My First Guitar (5)",
            normalized_title="my first guitar (5)",
            sync_id="sync_tampered_track_2693",
            musicbrainz_id="mbid-stale-target",
            artist=artist,
            album=album,
            duration=file_dur_ms,
            echosync_signature="CORRUPTED_SIGNATURE_HEX",
            metadata_status={"echosync_signature": "CORRUPTED_SIGNATURE_HEX"},
        )
        session.add(track)
        session.flush()

        media = LocalMedia(
            track_id=track.id,
            file_path=str(audio_file),
            file_format="flac",
            media_id="media_tampered_01",
        )
        session.add(media)

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "My First Guitar (5)",
            "artist": "Bon Jovi",
            "album": "Unknown Album",
            "musicbrainz_id": "mbid-stale-target",
            "echosync_signature": "CORRUPTED_SIGNATURE_HEX",
            "duration_ms": file_dur_ms,
            "channels": 2,
        },
    )

    # Signature verification fails (tampered/mismatched)
    monkeypatch.setattr(
        echosync_core,
        "verify_audio_signature",
        lambda path, title, artist, sig: False,
    )

    new_signatures_generated = []

    def mock_gen_sig(p, title, artist):
        sig = f"VALID_SIG_{title}_{artist}"
        new_signatures_generated.append((p, sig))
        return sig

    monkeypatch.setattr(echosync_core, "generate_audio_signature", mock_gen_sig)

    dummy_chromaprint = "A" * 60
    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: (dummy_chromaprint, file_dur_ms / 1000.0),
    )

    # MBID fetch returns candidate that fails trust gate against baseline title
    mock_mb = MagicMock()
    mock_mb.capabilities = type("Caps", (), {"supports_batching": False})()
    mock_mb.get_metadata.side_effect = lambda mbid: (
        {
            "title": "I Wrote You a Song",
            "artist": "Bon Jovi",
            "album": "Forever",
            "year": 2024,
        }
        if mbid == "mbid-stale-target"
        else {
            "title": "Living Proof",
            "artist": "Bon Jovi",
            "album": "Forever",
            "year": 2024,
            "release_id": "rel-bonjovi-lp",
            "release_group": {"primary_type": "Album"},
        }
    )

    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "acoustid-bonjovi-lp",
        "score": 0.97,
        "recordings": [
            {
                "id": "mbid-living-proof",
                "title": "Living Proof",
                "artist": "Bon Jovi",
                "duration": file_dur_ms / 1000.0,
                "score": 0.97,
            }
        ],
        "mbids": ["mbid-living-proof"],
    }

    def plugin_resolver(name):
        if name in (1990722619, "EchoSync.musicbrainz", "musicbrainz") or "musicbrainz" in str(name).lower():
            return mock_mb
        if name in (3801077393, "EchoSync.acoustid", "acoustid") or "acoustid" in str(name).lower():
            return mock_acoustid
        return None

    monkeypatch.setattr(PluginRegistry, "get_plugin", plugin_resolver)
    monkeypatch.setattr(
        PluginRegistry,
        "get_plugins_with_capability",
        lambda cap: (
            [mock_acoustid]
            if cap == Capability.RESOLVE_FINGERPRINT
            else ([mock_mb] if cap == Capability.FETCH_METADATA else [])
        ),
    )

    monkeypatch.setattr("core.path_formatter.ensure_path_invariance", lambda session, track, media: None)
    monkeypatch.setattr(RetroactiveEnhancer, "tag_file_verified", lambda self, path, tags: tags)

    enhancer = RetroactiveEnhancer()
    enhancer.enhance_library_metadata(batch_size=1, limit=1, check_all_files=False)

    # Invariants:
    # 1. Invalid signature was voided; track demoted to acoustic waterfall and resolved as 'Living Proof'
    # 2. SuggestionStagingQueue has NO staged review items
    # 3. New valid signature was stamped
    with music_db.session_scope() as session:
        t = session.query(Track).filter_by(sync_id="sync_tampered_track_2693").first()
        assert t is not None
        assert t.title == "Living Proof"
        assert t.musicbrainz_id == "mbid-living-proof"
        assert t.echosync_signature is not None
        assert t.echosync_signature.startswith("VALID_SIG_Living Proof")

    with working_db.session_scope() as session:
        staged = session.query(SuggestionStagingQueue).all()
        assert len(staged) == 0
