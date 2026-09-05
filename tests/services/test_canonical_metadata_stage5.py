"""
Stage 5 Test Suite: Canonical Singles Normalization, Band Member Disambiguation,
Canonical Studio Realignment for Repacks, Zero Telemetry Tags, and Reorganizer Retroactive Run.
"""

import uuid
from pathlib import Path
from unittest.mock import patch

import echosync_core

from core.path_formatter import build_destination_path
from database.music_database import Album, Artist, LocalMedia, Track, get_database
from services.library_reorganizer import LibraryReorganizerService
from services.metadata_enhancer import (
    MetadataEnhancerService,
    apply_ensemble_disambiguation,
    build_native_tag_payload,
    normalize_singles_metadata,
    realign_repack_metadata,
)
from tests.core.test_metadata_writer import (
    _create_minimal_flac_file,
    _create_minimal_m4a_file,
    _create_minimal_mp3_file,
    _create_minimal_wav_file,
)


def test_repack_canonical_realignment(tmp_path):
    """
    Asserts compilation track is realigned to original studio album,
    stamps REPACK_SOURCE and REPACK_RELEASE_MBID natively, and preserves provenance.
    """
    enhancer = MetadataEnhancerService()
    audio_file = _create_minimal_flac_file(tmp_path / "repack_track.flac")

    # Simulated track from compilation "Now That's What I Call Music! 50"
    initial_meta = {
        "title": "Yellow",
        "artist": "Coldplay",
        "album": "Now That's What I Call Music! 50",
        "musicbrainz_album_id": "compilation-release-mbid-123",
        "musicbrainz_track_id": "yellow-recording-mbid-456",
        "year": "2001",
    }

    # Resolved studio release candidate
    studio_candidate = {
        "canonical_studio_album": "Parachutes",
        "canonical_studio_release_mbid": "parachutes-release-mbid-789",
        "canonical_studio_release_group_mbid": "parachutes-rg-mbid-000",
        "canonical_year": 2000,
    }

    realigned_meta = realign_repack_metadata(initial_meta, studio_candidate)

    assert realigned_meta["album"] == "Parachutes"
    assert realigned_meta["musicbrainz_album_id"] == "parachutes-release-mbid-789"
    assert realigned_meta["musicbrainz_release_group_id"] == "parachutes-rg-mbid-000"
    assert realigned_meta["repack_source"] == "Now That's What I Call Music! 50"
    assert realigned_meta["repack_release_mbid"] == "compilation-release-mbid-123"
    assert realigned_meta["year"] == 2000

    # Stamp physical file via tag_file_verified
    verified_tags = enhancer.tag_file_verified(audio_file, realigned_meta)
    assert verified_tags is not None

    # Read back natively via echosync_core
    readback = echosync_core.read_metadata(str(audio_file))
    assert readback.get("repack_source") == "Now That's What I Call Music! 50"
    assert readback.get("repack_release_mbid") == "compilation-release-mbid-123"
    assert readback.get("release_group_id") == "parachutes-rg-mbid-000"


def test_singles_normalization_path(tmp_path):
    """
    Asserts [standalone recordings], [non-album tracks], and singles are normalized
    to Singles directory and follow singles_pattern.
    """
    lib_root = tmp_path / "music_library"
    album_pattern = "{Artist}/{Album}/{Track} - {Title}.{ext}"
    singles_pattern = "{Artist}/Singles/{Track} - {Title}.{ext}"

    # Test 1: [standalone recordings]
    raw_meta1 = {
        "artist": "Martin Garrix",
        "title": "Animals",
        "album": "[standalone recordings]",
        "track_number": None,
    }
    normalized1 = normalize_singles_metadata(dict(raw_meta1))
    assert normalized1["album"] == "Singles"
    assert normalized1["release_type"] == "single"
    assert normalized1["is_single"] is True

    p1 = build_destination_path(
        base_library_path=str(lib_root),
        pattern=album_pattern,
        meta=normalized1,
        ext="flac",
        singles_pattern=singles_pattern,
    )
    expected_p1 = lib_root / "Martin Garrix" / "Singles" / "Animals.flac"
    assert p1 == expected_p1

    # Test 2: [non-album tracks] with track number 0
    raw_meta2 = {
        "artist": "Daft Punk",
        "title": "Get Lucky",
        "album": "[non-album tracks]",
        "track_number": 0,
    }
    normalized2 = normalize_singles_metadata(dict(raw_meta2))
    p2 = build_destination_path(
        base_library_path=str(lib_root),
        pattern=album_pattern,
        meta=normalized2,
        ext="mp3",
        singles_pattern=singles_pattern,
    )
    expected_p2 = lib_root / "Daft Punk" / "Singles" / "Get Lucky.mp3"
    assert p2 == expected_p2


def test_band_member_album_artist_preservation(tmp_path):
    """
    Asserts ensemble solo track sets AlbumArtist = Band while preserving
    TrackArtist = Member in tags and path resolution.
    """
    audio_file = _create_minimal_flac_file(tmp_path / "solo_member.flac")
    enhancer = MetadataEnhancerService()

    track_meta = {
        "title": "Tunnel Vision",
        "artist": "RZA",
        "album": "Digital Bullet",
        "year": "2001",
    }

    # Disambiguate ensemble: member RZA is in Wu-Tang Clan
    disambiguated = apply_ensemble_disambiguation(track_meta, "Wu-Tang Clan")
    assert disambiguated["artist"] == "RZA"
    assert disambiguated["album_artist"] == "Wu-Tang Clan"

    # Verify native tag write
    verified_tags = enhancer.tag_file_verified(audio_file, disambiguated)
    assert verified_tags is not None

    readback = echosync_core.read_metadata(str(audio_file))
    assert readback.get("artist") == "RZA"
    assert readback.get("album_artist") == "Wu-Tang Clan"

    # Verify destination path places under Wu-Tang Clan folder
    dest_path = build_destination_path(
        base_library_path=str(tmp_path / "music"),
        pattern="{Artist}/{Album}/{Title}.{ext}",
        meta=disambiguated,
        ext="flac",
    )
    assert "Wu-Tang Clan" in dest_path.parts


def test_zero_telemetry_tags(tmp_path):
    """
    Strictly verifies NO proprietary machine-tracking UUIDs (ECHOSYNC_INSTANCE_UUID,
    ECHOSYNC_TRACK_UUID, ECHOSYNC_MEDIA_UUID) are written to audio files or generated
    in payload.
    """
    for ext, creator in [
        ("flac", _create_minimal_flac_file),
        ("mp3", _create_minimal_mp3_file),
        ("wav", _create_minimal_wav_file),
        ("m4a", _create_minimal_m4a_file),
    ]:
        audio_file = creator(tmp_path / f"privacy_test.{ext}")
        meta = {
            "title": "Zero Telemetry Track",
            "artist": "Privacy Artist",
            "album": "Clean Record",
            "isrc": "USPR12345678",
            "echosync_instance_uuid": "proprietary-instance-uuid",
            "echosync_track_uuid": "proprietary-track-uuid",
            "echosync_media_uuid": "proprietary-media-uuid",
        }

        payload = build_native_tag_payload(meta)
        assert "echosync_instance_uuid" not in payload
        assert "echosync_track_uuid" not in payload
        assert "echosync_media_uuid" not in payload

        echosync_core.write_metadata(str(audio_file), payload)
        readback = echosync_core.read_metadata(str(audio_file))

        assert "echosync_instance_uuid" not in readback
        assert "echosync_track_uuid" not in readback
        assert "echosync_media_uuid" not in readback


def test_reorganize_library_retroactive_run(tmp_path):
    """
    Verifies running reorganize_library realigns existing files in the library cleanly
    via Gatekeeper, normalizes singles and repacks, and updates local_media.file_path in music.db.
    """
    music_db = get_database()
    suffix = uuid.uuid4().hex[:6]

    library_dir = tmp_path / "library"
    library_dir.mkdir(parents=True, exist_ok=True)

    # Create test physical audio file in a staging directory
    staging_file = _create_minimal_flac_file(
        library_dir / f"incoming_raw_{suffix}.flac"
    )

    # Stamp repack tag on physical file
    echosync_core.write_metadata(
        str(staging_file),
        {
            "title": f"Stage5 Track {suffix}",
            "artist": f"Artist {suffix}",
            "album": "Original Studio Master",
            "repack_source": "Now 99",
            "repack_release_mbid": "repack-mbid-99",
        },
    )

    with music_db.session_scope() as session:
        artist = Artist(name=f"Artist {suffix}")
        session.add(artist)
        session.flush()

        album = Album(title="Original Studio Master", artist_id=artist.id)
        session.add(album)
        session.flush()

        track = Track(
            title=f"Stage5 Track {suffix}",
            artist_id=artist.id,
            album_id=album.id,
            track_number=1,
            sync_id=f"sync_{suffix}",
            release_type="album",
        )
        session.add(track)
        session.flush()

        media = LocalMedia(
            track_id=track.id,
            file_path=str(staging_file),
            media_id=f"m_{suffix}",
            file_format="flac",
        )
        session.add(media)
        session.commit()
        track_id = track.id

    # Configure reorganizer service pointing to library_dir
    reorganizer = LibraryReorganizerService()
    reorganizer.library_root = library_dir

    # Allow tmp_path in Gatekeeper roots for test execution
    from core.io_gatekeeper import Gatekeeper

    orig_get_roots = Gatekeeper._get_default_allowed_roots

    def mock_roots(self_gk):
        roots = orig_get_roots(self_gk)
        roots.append(tmp_path.resolve())
        return roots

    with patch.object(
        Gatekeeper, "_get_default_allowed_roots", side_effect=mock_roots, autospec=True
    ):
        # Run library reorganization targeting this track
        reorganizer.reorganize_library(track_ids=[track_id])

    # Verify physical file was moved into structured folder hierarchy
    with music_db.session_scope() as session:
        updated_media = (
            session.query(LocalMedia)
            .filter(LocalMedia.media_id == f"m_{suffix}")
            .first()
        )
        assert updated_media is not None
        new_path = Path(updated_media.file_path)
        assert new_path.exists()
        assert new_path.resolve() != staging_file.resolve()
        assert f"Artist {suffix}" in new_path.parts
        assert "Original Studio Master" in new_path.parts
