from sqlalchemy.orm import Session
from database.music_database import Track, Artist, TrackArtist
from core.matching_engine.text_utils import normalize_artist
from core.matching_engine.track_parser import extract_version_descriptors, decompose_artists
from core.db.echo_sync_track import EchosyncTrack


class ResolutionAdapter:
    """
    Adapter to translate EchosyncTrack memory models into SQLAlchemy ORM entities.
    Enforces strict boundaries for relational junction table hydration and lossless
    version extraction.
    """

    def reconcile_artist(self, name: str, session: Session) -> Artist:
        """
        Perform a normalized deduplication lookup before creating a new Artist row.
        """
        clean_name = name.strip()
        norm_name = normalize_artist(clean_name)

        # Deduplication lookup using normalized name
        artist = session.query(Artist).filter(Artist.normalized_name == norm_name).first()

        if not artist:
            artist = Artist(name=clean_name, normalized_name=norm_name)
            session.add(artist)
            session.flush()

        return artist

    def hydrate_track(self, result: EchosyncTrack, session: Session, track: Track) -> Track:
        """
        Safely update scalar fields on the Track ORM model, enforce relational
        artist reconciliation, and extract lossless editions.
        """
        # 1. Safely update basic track scalar fields
        if getattr(result, "title", None):
            track.title = result.title

        if getattr(result, "track_number", None) is not None:
            track.track_number = result.track_number

        if getattr(result, "disc_number", None) is not None:
            track.disc_number = result.disc_number

        if getattr(result, "isrc", None):
            track.isrc = result.isrc

        if getattr(result, "duration", None):
            d_val = result.duration
            track.duration = d_val if d_val > 1000 else int(d_val * 1000)
        elif getattr(result, "duration_ms", None):
            track.duration = result.duration_ms

        mbid = getattr(result, "musicbrainz_id", None) or getattr(result, "musicbrainz_track_id", None)
        if mbid:
            track.musicbrainz_id = mbid

        if getattr(result, "sync_id", None) and not track.sync_id:
            track.sync_id = result.sync_id

        # 2. Extract Lossless Editions
        raw_title = track.title or ""
        clean_title, ext_version, ext_edition = extract_version_descriptors(raw_title)

        if clean_title:
            track.title = clean_title

        # Cleanse album release title (e.g. "Dusk Till Dawn (radio edit)" -> "Dusk Till Dawn")
        raw_album = (
            getattr(result, "album_title", None)
            or getattr(result, "album", None)
            or (track.album.title if track.album else "")
        )
        clean_album, alb_version, alb_edition = (
            extract_version_descriptors(raw_album) if raw_album else (None, None, None)
        )
        if clean_album and track.album:
            track.album.title = clean_album

        if getattr(result, "edition", None):
            track.edition = result.edition
        elif ext_edition:
            track.edition = ext_edition
        elif ext_version:
            track.edition = ext_version
        elif alb_edition:
            track.edition = alb_edition
        elif alb_version:
            track.edition = alb_version
        elif getattr(result, "version", None):
            track.edition = result.version

        try:
            if ext_version:
                track.version = ext_version
            elif alb_version:
                track.version = alb_version
            elif getattr(result, "version", None):
                track.version = result.version
        except Exception:
            pass

        # 3. Enforce Relational Artist Reconciliation
        if getattr(result, "primary_artists", None):
            primary = result.primary_artists
            featured = getattr(result, "featured_artists", [])
            remixers = getattr(result, "remixers", [])
        else:
            artist_str = getattr(result, "artist_name", None) or getattr(result, "artist", "")
            roles = decompose_artists(artist_str)
            primary = roles.get("primary", [])
            featured = roles.get("featured", [])
            remixers = roles.get("remixer", [])

        # Fallback if decomposition fails
        if not primary and (getattr(result, "artist", None) or getattr(result, "artist_name", None)):
            fallback_artist = (result.artist if hasattr(result, "artist") else result.artist_name).strip()
            if fallback_artist:
                primary = [fallback_artist]
        if not primary:
            primary = ["Unknown Artist"]

        # Clear any existing track.artists relationships
        track.artist_associations.clear()

        main_artist = None
        position = 0

        # Iterate through primary_artists
        for name in primary:
            artist = self.reconcile_artist(name, session)
            if main_artist is None:
                main_artist = artist
            track.artist_associations.append(TrackArtist(artist=artist, role="primary", position=position))
            position += 1

        # Iterate through featured_artists
        for name in featured:
            artist = self.reconcile_artist(name, session)
            track.artist_associations.append(TrackArtist(artist=artist, role="featured", position=position))
            position += 1

        # Iterate through remixers
        for name in remixers:
            artist = self.reconcile_artist(name, session)
            track.artist_associations.append(TrackArtist(artist=artist, role="remixer", position=position))
            position += 1

        # Enforce NOT NULL constraint on Track.artist_id
        if main_artist:
            track.artist = main_artist

        return track
