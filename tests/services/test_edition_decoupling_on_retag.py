import pytest
from database import _canonicalize_path
from database.music_database import Album, Artist, Base, LocalMedia, Track, MusicDatabase, generate_nanoid
from database.working_database import WorkingBase, get_working_database
from core.db.echo_sync_track import EchosyncTrack
from core.metadata.adapter import reconcile_media_assignment
from web.routes.metadata_review import _import_single_file


@pytest.fixture
def test_dbs(tmp_path):
    music_db = MusicDatabase(tmp_path / "music.db")
    Base.metadata.create_all(music_db.engine)
    w_db = get_working_database()
    WorkingBase.metadata.create_all(w_db.engine)
    return music_db


def test_edition_decoupling_on_retag_approval(test_dbs, tmp_path, monkeypatch):
    """
    When a Track has multiple LocalMedia files (e.g. Natural and Bad Liar accidentally sharing a track_id),
    approving metadata for Bad Liar must decouple it into a new Track entity with its own sync_id,
    leaving Natural intact on the original track entity.
    """
    monkeypatch.setattr("web.routes.metadata_review.get_database", lambda: test_dbs)

    f_natural = tmp_path / "05 - Natural.flac"
    f_natural.write_bytes(b"audio_natural")
    f_bad_liar = tmp_path / "05 - Bad Liar.flac"
    f_bad_liar.write_bytes(b"audio_bad_liar")

    orig_sync_id = f"sid_{generate_nanoid(8)}"
    mid_nat = f"mid_{generate_nanoid(8)}"
    mid_liar = f"mid_{generate_nanoid(8)}"

    with test_dbs.session_scope() as session:
        artist = Artist(name="Imagine Dragons", normalized_name="imagine dragons")
        album = Album(title="Origins", normalized_title="origins", artist=artist)
        session.add_all([artist, album])
        session.flush()

        # Erroneously collapsed track sharing both files
        shared_track = Track(
            title="Natural",
            normalized_title="natural",
            sync_id=orig_sync_id,
            artist_id=artist.id,
            album_id=album.id,
            duration=189000,
        )
        session.add(shared_track)
        session.flush()

        m_nat = LocalMedia(
            track_id=shared_track.id,
            media_id=mid_nat,
            file_path=_canonicalize_path(str(f_natural)),
            file_format="flac",
        )
        m_liar = LocalMedia(
            track_id=shared_track.id,
            media_id=mid_liar,
            file_path=_canonicalize_path(str(f_bad_liar)),
            file_format="flac",
        )
        session.add_all([m_nat, m_liar])
        session.commit()
        shared_track_id = shared_track.id

    # Approve review metadata targeting Bad Liar
    bad_liar_metadata = {
        "title": "Bad Liar",
        "artist": "Imagine Dragons",
        "album": "Origins",
        "year": 2018,
        "track_number": 7,
        "media_id": mid_liar,
    }

    res = _import_single_file(f_bad_liar, bad_liar_metadata, media_id=mid_liar)
    assert res == 1

    # Verify decoupling
    with test_dbs.session_scope() as session:
        # Original track should still exist, labeled Natural, retaining orig_sync_id
        orig_track = session.get(Track, shared_track_id)
        assert orig_track is not None
        assert orig_track.title == "Natural"
        assert orig_track.sync_id == orig_sync_id

        # Natural media still points to orig_track
        med_nat = session.query(LocalMedia).filter_by(media_id=mid_nat).one()
        assert med_nat.track_id == orig_track.id

        # Bad Liar media now points to a NEW decoupled track
        med_liar = session.query(LocalMedia).filter_by(media_id=mid_liar).one()
        assert med_liar.track_id != orig_track.id

        decoupled_track = session.get(Track, med_liar.track_id)
        assert decoupled_track is not None
        assert decoupled_track.title == "Bad Liar"
        assert decoupled_track.sync_id != orig_sync_id
        assert len(decoupled_track.sync_id) > 0
        assert decoupled_track.album.title == "Origins"
        assert decoupled_track.artist.name == "Imagine Dragons"


def test_edition_decoupling_on_edition_divergence(test_dbs, tmp_path, monkeypatch):
    """
    When a track has multiple editions, retagging one edition with a distinct edition/version
    (e.g. Acoustic) decouples it into a distinct Track entity, preserving the base track.
    """
    monkeypatch.setattr("web.routes.metadata_review.get_database", lambda: test_dbs)

    f_orig = tmp_path / "Radioactive.flac"
    f_orig.write_bytes(b"audio1")
    f_acoustic = tmp_path / "Radioactive (Acoustic).flac"
    f_acoustic.write_bytes(b"audio2")

    orig_sync_id = f"sid_{generate_nanoid(8)}"
    mid_orig = f"mid_{generate_nanoid(8)}"
    mid_ac = f"mid_{generate_nanoid(8)}"

    with test_dbs.session_scope() as session:
        artist = Artist(name="Imagine Dragons", normalized_name="imagine dragons")
        album = Album(title="Night Visions", normalized_title="night visions", artist=artist)
        session.add_all([artist, album])
        session.flush()

        base_track = Track(
            title="Radioactive",
            normalized_title="radioactive",
            edition=None,
            sync_id=orig_sync_id,
            artist_id=artist.id,
            album_id=album.id,
        )
        session.add(base_track)
        session.flush()

        m_orig = LocalMedia(
            track_id=base_track.id,
            media_id=mid_orig,
            file_path=_canonicalize_path(str(f_orig)),
            file_format="flac",
        )
        m_ac = LocalMedia(
            track_id=base_track.id,
            media_id=mid_ac,
            file_path=_canonicalize_path(str(f_acoustic)),
            file_format="flac",
        )
        session.add_all([m_orig, m_ac])
        session.commit()
        base_track_id = base_track.id

    # Retag m_ac with edition "Acoustic"
    acoustic_metadata = {
        "title": "Radioactive",
        "edition": "Acoustic",
        "artist": "Imagine Dragons",
        "album": "Night Visions",
        "media_id": mid_ac,
    }

    _import_single_file(f_acoustic, acoustic_metadata, media_id=mid_ac)

    with test_dbs.session_scope() as session:
        t_base = session.get(Track, base_track_id)
        assert t_base.edition is None

        med_orig = session.query(LocalMedia).filter_by(media_id=mid_orig).one()
        assert med_orig.track_id == base_track_id

        med_ac = session.query(LocalMedia).filter_by(media_id=mid_ac).one()
        assert med_ac.track_id != base_track_id

        t_ac = session.get(Track, med_ac.track_id)
        assert t_ac.title == "Radioactive"
        assert t_ac.edition == "Acoustic"
        assert t_ac.sync_id != orig_sync_id


def test_single_media_track_updates_in_place(test_dbs, tmp_path, monkeypatch):
    """
    When a track has only ONE LocalMedia file, editing its metadata updates the Track in-place
    without spawning a new entity or altering its sync_id.
    """
    monkeypatch.setattr("web.routes.metadata_review.get_database", lambda: test_dbs)

    f_believer = tmp_path / "Believer.flac"
    f_believer.write_bytes(b"audio_believer")

    orig_sync_id = f"sid_{generate_nanoid(8)}"
    mid_bel = f"mid_{generate_nanoid(8)}"

    with test_dbs.session_scope() as session:
        artist = Artist(name="Imagine Dragons", normalized_name="imagine dragons")
        album = Album(title="Evolve", normalized_title="evolve", artist=artist)
        session.add_all([artist, album])
        session.flush()

        track = Track(
            title="Believer",
            normalized_title="believer",
            sync_id=orig_sync_id,
            artist_id=artist.id,
            album_id=album.id,
        )
        session.add(track)
        session.flush()

        media = LocalMedia(
            track_id=track.id,
            media_id=mid_bel,
            file_path=_canonicalize_path(str(f_believer)),
            file_format="flac",
        )
        session.add(media)
        session.commit()
        track_id = track.id

    updated_meta = {
        "title": "Believer",
        "edition": "Remix",
        "artist": "Imagine Dragons",
        "album": "Evolve",
        "media_id": mid_bel,
    }

    _import_single_file(f_believer, updated_meta, media_id=mid_bel)

    with test_dbs.session_scope() as session:
        t = session.get(Track, track_id)
        assert t is not None
        assert t.id == track_id
        assert t.sync_id == orig_sync_id
        assert t.edition == "Remix"


def test_reconcile_media_assignment_decouples_on_title_divergence(test_dbs, tmp_path):
    """
    Directly verify ResolutionAdapter.reconcile_media_assignment decouples a LocalMedia
    when its title diverges, even in the absence of chromaprints or MBIDs.
    """
    with test_dbs.session_scope() as session:
        artist = Artist(name="Queen", normalized_name="queen")
        album = Album(title="A Night at the Opera", normalized_title="a night at the opera", artist=artist)
        session.add_all([artist, album])
        session.flush()

        parent_track = Track(
            title="Bohemian Rhapsody",
            normalized_title="bohemian rhapsody",
            sync_id=f"sid_{generate_nanoid(8)}",
            artist_id=artist.id,
            album_id=album.id,
        )
        session.add(parent_track)
        session.flush()

        m1 = LocalMedia(
            track_id=parent_track.id,
            media_id=f"mid_{generate_nanoid(8)}",
            file_path="/music/Bohemian Rhapsody.flac",
            file_format="flac",
        )
        m2 = LocalMedia(
            track_id=parent_track.id,
            media_id=f"mid_{generate_nanoid(8)}",
            file_path="/music/Love of My Life.flac",
            file_format="flac",
        )
        session.add_all([m1, m2])
        session.flush()

        dto_divergent = EchosyncTrack(
            raw_title="Love of My Life",
            artist_name="Queen",
            album_title="A Night at the Opera",
        )

        reconciled = reconcile_media_assignment(
            session=session,
            media=m2,
            enhanced_dto=dto_divergent,
        )

        assert reconciled.id != parent_track.id
        assert m2.track_id == reconciled.id
        assert reconciled.title == "Love of My Life"
        assert m1.track_id == parent_track.id
        assert session.get(Track, parent_track.id).title == "Bohemian Rhapsody"
