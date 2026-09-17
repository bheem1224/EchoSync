"""
Unit and integration tests for Stage 2:
- First-Class Entity Aliases & KVS Attributes Schema
- Governed SDK Mutation Brokers (sdk.aliases, sdk.attributes)
- CJK Language Pack Plugin Governance & Self-Healing Worker
- Rich Track Endpoint Serialization
"""

import binascii

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.database.repositories.track_repo import TrackRepository
from core.metadata.schemas import EntityAliasProposal
from core.nexus_framework.plugin_SDK import (
    _AliasBroker,
    _AttributeBroker,
    _validate_attribute_payload,
)
from database.music_database import (
    Album,
    AlbumAttribute,
    Artist,
    ArtistAlias,
    ArtistAttribute,
    Base,
    Track,
    TrackAlias,
    TrackAttribute,
    _ensure_alias_and_attribute_schema,
)
from plugins.EchoSync.cjk_language_pack.plugin import (
    CJKLanguagePackPlugin,
    extract_mb_aliases,
)


@pytest.fixture
def memory_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    _ensure_alias_and_attribute_schema(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    return engine, Session


def test_schema_and_models(memory_db):
    engine, Session = memory_db
    with Session() as session:
        artist = Artist(name="米津玄師", normalized_name="kenshi yonezu")
        album = Album(title="STRAY SHEEP", normalized_title="stray sheep", artist=artist)
        track = Track(title="Lemon", normalized_title="lemon", artist=artist, album=album, sync_id="track123")
        session.add_all([artist, album, track])
        session.flush()

        # Add TrackAlias & ArtistAlias with plugin_id
        crc = binascii.crc32(b"cjk_language_pack") & 0xFFFFFFFF
        t_alias = TrackAlias(
            track_id=track.id,
            plugin_id=crc,
            name="Lemon (Romaji)",
            locale="en",
            script="Latn",
            alias_type="transliteration",
        )
        a_alias = ArtistAlias(
            artist_id=artist.id,
            plugin_id=crc,
            name="Kenshi Yonezu",
            locale="en",
            script="Latn",
            alias_type="transliteration",
        )
        session.add_all([t_alias, a_alias])

        # Add attributes
        t_attr = TrackAttribute(track_id=track.id, plugin_id=crc, key="cjk_enhanced", value=True)
        a_attr = ArtistAttribute(artist_id=artist.id, plugin_id=crc, key="origin", value={"country": "JP"})
        alb_attr = AlbumAttribute(album_id=album.id, plugin_id=crc, key="verified", value=1)
        session.add_all([t_attr, a_attr, alb_attr])
        session.commit()

        # Query back
        reloaded_track = session.query(Track).filter_by(id=track.id).first()
        assert len(reloaded_track.aliases) == 1
        assert reloaded_track.aliases[0].name == "Lemon (Romaji)"
        assert reloaded_track.aliases[0].plugin_id == crc

        assert len(reloaded_track.attributes) == 1
        assert reloaded_track.attributes[0].key == "cjk_enhanced"
        assert reloaded_track.attributes[0].value is True


def test_track_repo_alias_and_attribute_operations(memory_db):
    engine, Session = memory_db
    crc = 999888777
    with Session() as session:
        artist = Artist(name="周杰倫", normalized_name="jay chou")
        track = Track(title="晴天", normalized_title="qing tian", artist=artist, sync_id="jay001")
        session.add_all([artist, track])
        session.flush()

        # Upsert aliases via TrackRepository
        proposals = [
            EntityAliasProposal(
                entity_type="artist",
                entity_id=artist.id,
                value="Jay Chou",
                language="en",
                script="Latn",
                alias_type="pinyin",
            ),
            EntityAliasProposal(
                entity_type="track",
                entity_id=track.id,
                value="Qing Tian",
                language="en",
                script="Latn",
                alias_type="pinyin",
            ),
        ]
        count = TrackRepository.upsert_entity_aliases(
            session=session, proposals=proposals, sync_id=track.sync_id, plugin_id=crc, commit=True
        )
        assert count == 2

        # Verify aliases were persisted
        aliases = session.query(TrackAlias).filter_by(track_id=track.id).all()
        assert len(aliases) == 1
        assert aliases[0].name == "Qing Tian"
        assert aliases[0].plugin_id == crc

        # Test Attribute KVS CRUD
        TrackRepository.set_entity_attributes(
            session=session,
            entity_type="track",
            entity_id=track.id,
            plugin_id=crc,
            key="analysis.mood",
            value={"energy": 0.85, "tags": ["nostalgic", "sunny"]},
            commit=True,
        )

        attrs = TrackRepository.get_entity_attributes(
            session=session, entity_type="track", entity_id=track.id, plugin_id=crc
        )
        assert attrs["analysis.mood"]["energy"] == 0.85

        # All plugins query
        all_attrs = TrackRepository.get_entity_attributes(
            session=session, entity_type="track", entity_id=track.id, plugin_id=None
        )
        assert crc in all_attrs
        assert all_attrs[crc]["analysis.mood"]["energy"] == 0.85

        # Delete attribute
        deleted = TrackRepository.delete_entity_attribute(
            session=session,
            entity_type="track",
            entity_id=track.id,
            plugin_id=crc,
            key="analysis.mood",
            commit=True,
        )
        assert deleted is True

        attrs_after = TrackRepository.get_entity_attributes(
            session=session, entity_type="track", entity_id=track.id, plugin_id=crc
        )
        assert "analysis.mood" not in attrs_after


def test_attribute_payload_validation():
    # Valid key and values
    _validate_attribute_payload("valid.key_name-1", {"valid": [1, 2, 3]})
    _validate_attribute_payload("test", "simple_string")
    _validate_attribute_payload("number", 42)

    # Invalid key characters
    with pytest.raises(ValueError, match="Invalid attribute key"):
        _validate_attribute_payload("invalid/key", "val")

    with pytest.raises(ValueError, match="Invalid attribute key"):
        _validate_attribute_payload("key with spaces", "val")

    with pytest.raises(ValueError, match="Invalid attribute key"):
        _validate_attribute_payload("", "val")

    # Excessive recursion depth (> 5)
    deeply_nested = {"a": {"b": {"c": {"d": {"e": {"f": "too deep"}}}}}}
    with pytest.raises(ValueError, match="depth"):
        _validate_attribute_payload("deep", deeply_nested)

    # Payload exceeding 64 KB
    oversized = "x" * 70000
    with pytest.raises(ValueError, match="64 KB"):
        _validate_attribute_payload("big", oversized)


def test_alias_broker_permission_enforcement(monkeypatch, memory_db):
    engine, Session = memory_db
    broker = _AliasBroker("unauthorized_plugin")

    # Mock check_plugin_permission to return False
    monkeypatch.setattr(
        "core.nexus_framework.plugin_SDK.check_plugin_permission",
        lambda pid, scope: False,
    )

    with pytest.raises(PermissionError, match="lacks 'permissions.database.mutate_aliases'"):
        broker.upsert("track", 1, [{"name": "Test"}])


def test_attribute_broker_permission_enforcement(monkeypatch, memory_db):
    engine, Session = memory_db
    broker = _AttributeBroker("unauthorized_plugin")

    monkeypatch.setattr(
        "core.nexus_framework.plugin_SDK.check_plugin_permission",
        lambda pid, scope: False,
    )

    with pytest.raises(PermissionError, match="lacks 'permissions.database.mutate_attributes'"):
        broker.set("track", 1, "test_key", "value")

    with pytest.raises(PermissionError, match="lacks 'permissions.database.read_library'"):
        broker.get("track", 1, "test_key")


def test_cjk_plugin_extract_mb_aliases(monkeypatch, memory_db):
    engine, Session = memory_db

    # Grant cjk_language_pack required permissions
    monkeypatch.setattr(
        "core.nexus_framework.plugin_SDK.check_plugin_permission",
        lambda pid, scope: True,
    )

    with Session() as session:
        artist = Artist(name="YOASOBI", normalized_name="yoasobi")
        track = Track(
            title="アイドル",
            normalized_title="aidoru",
            artist=artist,
            sync_id="yoasobi01",
            metadata_status={"echosync_signature": "sig_abc_123"},
        )
        session.add_all([artist, track])
        session.flush()

        mb_data = {
            "aliases": [
                {"name": "Idol", "locale": "en", "script": "Latn", "type": "transliteration"},
                {"name": "アイドル (Official)", "locale": "ja", "script": "Jpan"},
            ],
            "artist-credit": [
                {
                    "artist": {
                        "name": "YOASOBI",
                        "aliases": [{"name": "Yoasobi", "locale": "en", "script": "Latn", "type": "transliteration"}],
                    }
                }
            ],
        }

        # Mock get_database to return our session
        class MockDB:
            def get_session(self):
                return session

        monkeypatch.setattr("database.music_database.get_database", lambda: MockDB())

        extract_mb_aliases(track, mb_data=mb_data)

        # Verify aliases were persisted
        aliases = session.query(TrackAlias).filter_by(track_id=track.id).all()
        assert len(aliases) >= 1
        alias_names = [a.name for a in aliases]
        assert "アイドル (Official)" in alias_names

        # Verify attribute status was set
        attrs = TrackRepository.get_entity_attributes(session=session, entity_type="track", entity_id=track.id)
        # Should have cjk_enhanced stamped
        assert any(p_attrs.get("cjk_enhanced") is True for p_attrs in attrs.values())


@pytest.mark.asyncio
async def test_cjk_plugin_self_healing_worker(monkeypatch, memory_db):
    engine, Session = memory_db

    monkeypatch.setattr(
        "core.nexus_framework.plugin_SDK.check_plugin_permission",
        lambda pid, scope: True,
    )

    with Session() as session:
        artist = Artist(name="米津玄師", normalized_name="kenshi yonezu")
        # Track 1: Has echosync_signature -> Eligible
        track1 = Track(
            title="打上花火",
            normalized_title="uchiage hanabi",
            artist=artist,
            sync_id="sig_track_01",
            metadata_status={"echosync_signature": "sig_valid_01"},
        )
        # Track 2: No echosync_signature -> Ineligible
        track2 = Track(
            title="Lemon",
            normalized_title="lemon",
            artist=artist,
            sync_id="nosig_track_02",
            metadata_status={},
        )
        session.add_all([artist, track1, track2])
        session.commit()

        class MockDB:
            def get_session(self):
                return Session()

        monkeypatch.setattr("database.music_database.get_database", lambda: MockDB())

        plugin = CJKLanguagePackPlugin()
        processed = await plugin.run_cjk_background_worker()

        # Track 1 was processed
        assert processed >= 1

        with Session() as verify_session:
            t1_attrs = TrackRepository.get_entity_attributes(
                session=verify_session, entity_type="track", entity_id=track1.id
            )
            assert any(p_attrs.get("cjk_enhanced") is True for p_attrs in t1_attrs.values())

            # Track 2 should not have cjk_enhanced
            t2_attrs = TrackRepository.get_entity_attributes(
                session=verify_session, entity_type="track", entity_id=track2.id
            )
            assert not any(p_attrs.get("cjk_enhanced") is True for p_attrs in t2_attrs.values())


def test_search_by_alias(memory_db):
    engine, Session = memory_db
    with Session() as session:
        artist = Artist(name="宇多田ヒカル", normalized_name="hikaru utada")
        track = Track(title="光", normalized_title="hikari", artist=artist, sync_id="utada01")
        session.add_all([artist, track])
        session.flush()

        t_alias = TrackAlias(track_id=track.id, name="Simple and Clean", locale="en", script="Latn")
        a_alias = ArtistAlias(artist_id=artist.id, name="Utada Hikaru", locale="en", script="Latn")
        session.add_all([t_alias, a_alias])
        session.commit()

        # Search by alias using MusicDatabase search
        class MockMusicDB:
            from contextlib import contextmanager

            @contextmanager
            def session_scope(self):
                with Session() as sess:
                    yield sess

        from database.music_database import MusicDatabase

        mock_db = MockMusicDB()
        results = MusicDatabase.search_library(mock_db, "Simple and Clean")
        assert len(results["tracks"]) == 1
        assert results["tracks"][0]["title"] == "光"

        results_artist = MusicDatabase.search_library(mock_db, "Utada Hikaru")
        assert len(results_artist["artists"]) == 1
        assert results_artist["artists"][0]["name"] == "宇多田ヒカル"


def test_rich_track_endpoint(memory_db, monkeypatch):
    engine, Session = memory_db
    with Session() as session:
        artist = Artist(name="RADWIMPS", normalized_name="radwimps")
        track = Track(title="前前前世", normalized_title="zenzenzense", artist=artist, sync_id="rad001")
        session.add_all([artist, track])
        session.flush()

        crc = 12345678
        t_alias = TrackAlias(track_id=track.id, plugin_id=crc, name="Zenzenzense", locale="en", script="Latn")
        t_attr = TrackAttribute(track_id=track.id, plugin_id=crc, key="theme_song", value="Your Name OST")
        session.add_all([t_alias, t_attr])
        session.commit()

        class MockDB:
            def get_session(self):
                return Session()

        monkeypatch.setattr("web.routes.tracks.get_database", lambda: MockDB())

        from fastapi.testclient import TestClient

        from web.api_app import create_app

        client = TestClient(create_app())

        # Test standard endpoint without rich
        res_standard = client.get("/api/v1/core/tracks/rad001")
        assert res_standard.status_code == 200
        standard_data = res_standard.json()
        assert "attributes" not in standard_data

        # Test rich endpoint on /api/v1/core/tracks/
        res_rich = client.get("/api/v1/core/tracks/rad001?rich=true")
        assert res_rich.status_code == 200
        rich_data = res_rich.json()
        assert "attributes" in rich_data
        assert str(crc) in rich_data["attributes"] or crc in rich_data["attributes"]
        attr_dict = rich_data["attributes"].get(str(crc)) or rich_data["attributes"].get(crc)
        assert attr_dict["theme_song"] == "Your Name OST"
        assert len(rich_data["aliases"]) == 1
        assert rich_data["aliases"][0]["name"] == "Zenzenzense"

        # Test /api/v1/library/track/ endpoint with rich=true
        res_lib = client.get("/api/v1/library/track/rad001?rich=true")
        assert res_lib.status_code == 200
        lib_data = res_lib.json()
        assert "attributes" in lib_data
