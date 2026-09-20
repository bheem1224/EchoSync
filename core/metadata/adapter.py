from sqlalchemy.orm import Session
from database.music_database import Track, Artist, TrackArtist, LocalMedia
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

    def prune_orphaned_track_if_empty(self, session: Session, track_id: int | None) -> bool:
        """
        Remove Track row and related junction/parent rows if no LocalMedia rows reference it.
        Never deletes physical files.
        """
        if not track_id:
            return False
        import logging
        from database.music_database import Album, LocalMedia, Track, TrackArtist

        logger = logging.getLogger(__name__)

        remaining = session.query(LocalMedia).filter(LocalMedia.track_id == track_id).count()
        if remaining == 0:
            track = session.get(Track, track_id)
            if track:
                album_id = track.album_id
                artist_id = track.artist_id
                logger.info("Pruning orphaned Track ID %d ('%s') with no remaining LocalMedia", track_id, track.title)
                session.query(TrackArtist).filter_by(track_id=track_id).delete()
                session.delete(track)
                session.flush()

                if album_id and session.query(Track).filter_by(album_id=album_id).count() == 0:
                    session.query(Album).filter_by(id=album_id).delete()

                if artist_id:
                    has_tracks = session.query(Track).filter_by(artist_id=artist_id).count() > 0
                    has_junctions = session.query(TrackArtist).filter_by(artist_id=artist_id).count() > 0
                    if not has_tracks and not has_junctions:
                        session.query(Artist).filter_by(id=artist_id).delete()
                return True
        return False

    def reconcile_media_assignment(
        self,
        session: Session,
        media: "LocalMedia",
        enhanced_dto: EchosyncTrack,
        current_chromaprint: str | None = None,
    ) -> Track:
        """
        Reconciles a LocalMedia file's track assignment post-enhancement:
        1. If a canonical Track already exists in the database matching MBID/ISRC,
           and its acoustic fingerprint matches (>= 0.90 similarity), re-link
           `media.track_id` to the existing canonical track (collapsing duplicate tracks into editions).
        2. If the media was grouped under a Track with multiple files, but its acoustic/metadata
           identity diverges from that Track, decouple it by instantiating a new discrete Track entity.
        3. If the media remains under its existing Track, hydrate the track with the enhanced metadata.
        4. Automatically prune any orphaned Track rows left with zero associated LocalMedia rows.
        """
        import logging
        from core.matching_engine.fingerprinting import FingerprintMatcher
        from database.music_database import generate_nanoid

        logger = logging.getLogger(__name__)

        mbid = getattr(enhanced_dto, "musicbrainz_id", None) or getattr(enhanced_dto, "musicbrainz_track_id", None)
        isrc = getattr(enhanced_dto, "isrc", None)
        old_track_id = media.track_id
        current_track = session.get(Track, old_track_id) if old_track_id else None

        # 1. Check for existing canonical Track to collapse into
        matched_track = None
        if mbid and mbid != "NOT_FOUND":
            cand_query = session.query(Track).filter(Track.musicbrainz_id == mbid)
            if old_track_id:
                cand_query = cand_query.filter(Track.id != old_track_id)
            candidates = cand_query.all()
            for cand in candidates:
                cand_fps = [fp.chromaprint for m in cand.media_files for fp in m.audio_fingerprints if fp.chromaprint]
                if current_chromaprint and cand_fps:
                    sims = [FingerprintMatcher.get_confidence_score(current_chromaprint, cfp) for cfp in cand_fps]
                    if any(s >= 0.90 for s in sims):
                        matched_track = cand
                        break
                elif not current_chromaprint:
                    matched_track = cand
                    break

        if not matched_track and isrc:
            cand_query = session.query(Track).filter(Track.isrc == isrc)
            if old_track_id:
                cand_query = cand_query.filter(Track.id != old_track_id)
            candidates = cand_query.all()
            for cand in candidates:
                cand_fps = [fp.chromaprint for m in cand.media_files for fp in m.audio_fingerprints if fp.chromaprint]
                if current_chromaprint and cand_fps:
                    sims = [FingerprintMatcher.get_confidence_score(current_chromaprint, cfp) for cfp in cand_fps]
                    if any(s >= 0.90 for s in sims):
                        matched_track = cand
                        break
                elif not current_chromaprint:
                    matched_track = cand
                    break

        if not matched_track:
            t_title = (getattr(enhanced_dto, "title", None) or "").strip()
            t_artist = (
                getattr(enhanced_dto, "artist", None) or getattr(enhanced_dto, "artist_name", None) or ""
            ).strip()
            t_edition = getattr(enhanced_dto, "edition", None)
            t_duration = getattr(enhanced_dto, "duration", None) or getattr(enhanced_dto, "duration_ms", None)

            if t_title and t_artist:
                from sqlalchemy import or_
                from core.matching_engine.text_utils import normalize_artist, normalize_title

                norm_title = normalize_title(t_title)
                norm_artist = normalize_artist(t_artist)

                cand_query = (
                    session.query(Track)
                    .join(Artist, Track.artist_id == Artist.id)
                    .filter(
                        Track.normalized_title == norm_title,
                        Artist.normalized_name == norm_artist,
                    )
                )
                if old_track_id:
                    cand_query = cand_query.filter(Track.id != old_track_id)

                if t_edition:
                    cand_query = cand_query.filter(Track.edition == t_edition)
                else:
                    cand_query = cand_query.filter(or_(Track.edition.is_(None), Track.edition == ""))

                if t_duration:
                    dur_val = t_duration if t_duration > 1000 else int(t_duration * 1000)
                    cand_query = cand_query.filter(Track.duration.between(dur_val - 3000, dur_val + 3000))

                candidates = cand_query.all()
                for cand in candidates:
                    cand_fps = [
                        fp.chromaprint for m in cand.media_files for fp in m.audio_fingerprints if fp.chromaprint
                    ]
                    if current_chromaprint and cand_fps:
                        sims = [FingerprintMatcher.get_confidence_score(current_chromaprint, cfp) for cfp in cand_fps]
                        if any(s >= 0.90 for s in sims):
                            matched_track = cand
                            break
                    elif not current_chromaprint:
                        matched_track = cand
                        break

        if matched_track:
            logger.info(
                "Reconciling LocalMedia %s (%s): collapsing into existing Track %s (MBID: %s)",
                media.id,
                media.file_path,
                matched_track.id,
                matched_track.musicbrainz_id,
            )
            media.track_id = matched_track.id
            session.flush()
            if old_track_id and old_track_id != matched_track.id:
                self.prune_orphaned_track_if_empty(session, old_track_id)
            return matched_track

        # 2. Check for decoupling from multi-media track
        if current_track and len(current_track.media_files) > 1:
            other_media = [m for m in current_track.media_files if m.id != media.id]
            diverges = False
            if current_track.musicbrainz_id and mbid and current_track.musicbrainz_id != mbid:
                diverges = True
            elif not (current_track.musicbrainz_id and mbid and current_track.musicbrainz_id == mbid):
                if current_chromaprint:
                    other_fps = [fp.chromaprint for m in other_media for fp in m.audio_fingerprints if fp.chromaprint]
                    if other_fps and not any(
                        FingerprintMatcher.get_confidence_score(current_chromaprint, ofp) >= 0.90 for ofp in other_fps
                    ):
                        diverges = True

            if diverges:
                logger.info(
                    "Reconciling LocalMedia %s (%s): decoupling from Track %s into new Track entity",
                    media.id,
                    media.file_path,
                    current_track.id,
                )
                new_track = Track(
                    title=enhanced_dto.title or current_track.title,
                    sync_id=generate_nanoid(8),
                    musicbrainz_id=mbid if mbid != "NOT_FOUND" else None,
                    isrc=isrc,
                    duration=enhanced_dto.duration or current_track.duration,
                    artist_id=getattr(enhanced_dto, "artist_id", None) or current_track.artist_id,
                    album_id=getattr(enhanced_dto, "album_id", None) or current_track.album_id,
                    metadata_status=dict(getattr(enhanced_dto, "metadata_status", None) or {}),
                )
                session.add(new_track)
                session.flush()
                new_track = self.hydrate_track(enhanced_dto, session, new_track)
                media.track_id = new_track.id
                session.flush()
                return new_track

        # 3. In-place track hydration
        if current_track:
            current_track = self.hydrate_track(enhanced_dto, session, current_track)
            if getattr(enhanced_dto, "album_id", None):
                current_track.album_id = enhanced_dto.album_id
            return current_track

        return None


def reconcile_media_assignment(
    session: Session,
    media: "LocalMedia",
    enhanced_dto: EchosyncTrack,
    current_chromaprint: str | None = None,
) -> Track:
    """Convenience functional wrapper for ResolutionAdapter.reconcile_media_assignment."""
    return ResolutionAdapter().reconcile_media_assignment(session, media, enhanced_dto, current_chromaprint)


def prune_orphaned_track_if_empty(session: Session, track_id: int | None) -> bool:
    """Convenience functional wrapper for ResolutionAdapter.prune_orphaned_track_if_empty."""
    return ResolutionAdapter().prune_orphaned_track_if_empty(session, track_id)
