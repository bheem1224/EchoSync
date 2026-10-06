import logging
from sqlalchemy.orm import Session
from database.music_database import Track, Artist, TrackArtist, LocalMedia, Album
from core.matching_engine.text_utils import normalize_artist
from core.matching_engine.track_parser import extract_version_descriptors, decompose_artists
from core.db.echo_sync_track import EchosyncTrack

logger = logging.getLogger(__name__)


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

        # Clear any existing track.artists relationships with explicit deletion flush ordering
        if track.id:
            session.query(TrackArtist).filter_by(track_id=track.id).delete(synchronize_session="fetch")
            session.flush()
        track.artist_associations.clear()

        main_artist = None
        position = 0
        seen_associations: set[tuple[int, str]] = set()

        # Iterate through primary_artists
        for name in primary:
            artist = self.reconcile_artist(name, session)
            if main_artist is None:
                main_artist = artist
            pair_key = (artist.id, "primary")
            if pair_key in seen_associations:
                logger.debug("Skipping duplicate artist association: artist_id=%s, role=primary", artist.id)
                continue
            seen_associations.add(pair_key)
            ta = (
                TrackArtist(track_id=track.id, artist_id=artist.id, role="primary", position=position)
                if track.id
                else TrackArtist(artist=artist, role="primary", position=position)
            )
            track.artist_associations.append(ta)
            position += 1

        # Iterate through featured_artists
        for name in featured:
            artist = self.reconcile_artist(name, session)
            pair_key = (artist.id, "featured")
            if pair_key in seen_associations:
                logger.debug("Skipping duplicate artist association: artist_id=%s, role=featured", artist.id)
                continue
            seen_associations.add(pair_key)
            ta = (
                TrackArtist(track_id=track.id, artist_id=artist.id, role="featured", position=position)
                if track.id
                else TrackArtist(artist=artist, role="featured", position=position)
            )
            track.artist_associations.append(ta)
            position += 1

        # Iterate through remixers
        for name in remixers:
            artist = self.reconcile_artist(name, session)
            pair_key = (artist.id, "remixer")
            if pair_key in seen_associations:
                logger.debug("Skipping duplicate artist association: artist_id=%s, role=remixer", artist.id)
                continue
            seen_associations.add(pair_key)
            ta = (
                TrackArtist(track_id=track.id, artist_id=artist.id, role="remixer", position=position)
                if track.id
                else TrackArtist(artist=artist, role="remixer", position=position)
            )
            track.artist_associations.append(ta)
            position += 1

        # Enforce NOT NULL constraint on Track.artist_id
        if main_artist:
            track.artist = main_artist
            track.artist_id = main_artist.id

        return track

    def prune_orphaned_track_if_empty(self, session: Session, track_id: int | None) -> bool:
        """
        Remove Track row and related junction rows if no LocalMedia rows reference it.
        Never deletes physical files or catalog entities (Albums/Artists).
        """
        if not track_id:
            return False
        import logging
        from database.music_database import LocalMedia, Track, TrackArtist

        logger = logging.getLogger(__name__)

        remaining = session.query(LocalMedia).filter(LocalMedia.track_id == track_id).count()
        if remaining == 0:
            track = session.get(Track, track_id)
            if track:
                logger.info("Pruning orphaned Track ID %d ('%s') with no remaining LocalMedia", track_id, track.title)
                track.media_files = []
                session.query(TrackArtist).filter_by(track_id=track_id).delete()
                session.delete(track)
                session.flush()
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
            media.track = matched_track
            media.track_id = matched_track.id
            session.flush()
            if old_track_id and old_track_id != matched_track.id:
                self.prune_orphaned_track_if_empty(session, old_track_id)

            # Verify matched_track still exists in DB
            db_track = session.get(Track, matched_track.id)
            if not db_track:
                logger.warning(
                    "Matched track %s no longer exists in database after pruning old track %s",
                    matched_track.id,
                    old_track_id,
                )
                return None

            # Verify matched_track's album_id exists in DB
            if matched_track.album_id and not session.query(Album.id).filter_by(id=matched_track.album_id).first():
                logger.warning(
                    "Matched track %s has invalid/stale album_id %s; resetting to None",
                    matched_track.id,
                    matched_track.album_id,
                )
                matched_track.album_id = None
            return matched_track

        # 2. Check for decoupling from multi-media track
        sibling_count = 0
        if current_track:
            sibling_count = (
                session.query(LocalMedia)
                .filter(LocalMedia.track_id == current_track.id, LocalMedia.id != media.id)
                .count()
            )

        if current_track and (sibling_count > 0 or len(current_track.media_files) > 1):
            other_media = [m for m in current_track.media_files if m.id != media.id]
            diverges = False
            if current_track.musicbrainz_id and mbid and current_track.musicbrainz_id != mbid:
                diverges = True
            else:
                dto_title = (getattr(enhanced_dto, "title", None) or getattr(enhanced_dto, "raw_title", None) or "").strip().lower()
                cur_title = (current_track.title or "").strip().lower()
                if dto_title and cur_title and dto_title != cur_title:
                    diverges = True

                dto_edition = (getattr(enhanced_dto, "edition", None) or getattr(enhanced_dto, "version", None) or "").strip().lower()
                cur_edition = (current_track.edition or "").strip().lower()
                if (dto_edition or cur_edition) and dto_edition != cur_edition:
                    diverges = True

                dto_artist = (getattr(enhanced_dto, "artist", None) or getattr(enhanced_dto, "artist_name", None) or "").strip().lower()
                cur_artist = (current_track.artist.name if current_track.artist else "").strip().lower()
                if dto_artist and cur_artist and dto_artist != cur_artist:
                    diverges = True

                dto_album = (getattr(enhanced_dto, "album", None) or getattr(enhanced_dto, "album_title", None) or "").strip().lower()
                cur_album = (current_track.album.title if current_track.album else "").strip().lower()
                if dto_album and cur_album and dto_album != cur_album:
                    diverges = True

                dto_isrc = (getattr(enhanced_dto, "isrc", None) or "").strip()
                cur_isrc = (current_track.isrc or "").strip()
                if dto_isrc and cur_isrc and dto_isrc != cur_isrc:
                    diverges = True

                if not diverges and current_chromaprint:
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
                from core.database.repositories.track_repo import TrackRepository
                TrackRepository.resolve_artists_and_albums(session, [enhanced_dto])

                target_album_id = getattr(enhanced_dto, "album_id", None)
                verified_album_id = None
                if target_album_id and session.query(Album.id).filter_by(id=target_album_id).first():
                    verified_album_id = target_album_id
                elif current_track.album_id and session.query(Album.id).filter_by(id=current_track.album_id).first():
                    dto_alb = (getattr(enhanced_dto, "album", None) or getattr(enhanced_dto, "album_title", None) or "").strip().lower()
                    cur_alb = (current_track.album.title if current_track.album else "").strip().lower()
                    if not dto_alb or dto_alb == cur_alb:
                        verified_album_id = current_track.album_id

                resolved_artist_id = getattr(enhanced_dto, "artist_id", None) or current_track.artist_id

                new_track = Track(
                    title=enhanced_dto.title or current_track.title,
                    sync_id=generate_nanoid(8),
                    edition=getattr(enhanced_dto, "edition", None) or getattr(enhanced_dto, "version", None),
                    musicbrainz_id=mbid if mbid != "NOT_FOUND" else None,
                    isrc=isrc,
                    duration=enhanced_dto.duration or current_track.duration,
                    track_number=getattr(enhanced_dto, "track_number", None) or current_track.track_number,
                    disc_number=getattr(enhanced_dto, "disc_number", None) or current_track.disc_number,
                    artist_id=resolved_artist_id,
                    album_id=verified_album_id,
                    metadata_status=dict(getattr(enhanced_dto, "metadata_status", None) or {}),
                )
                session.add(new_track)
                session.flush()
                new_track = self.hydrate_track(enhanced_dto, session, new_track)
                if verified_album_id:
                    new_track.album_id = verified_album_id
                media.track = new_track
                media.track_id = new_track.id
                session.flush()
                if old_track_id and old_track_id != new_track.id:
                    self.prune_orphaned_track_if_empty(session, old_track_id)
                return new_track

        # 3. In-place track hydration
        if current_track:
            from core.database.repositories.track_repo import TrackRepository
            TrackRepository.resolve_artists_and_albums(session, [enhanced_dto])
            current_track = self.hydrate_track(enhanced_dto, session, current_track)
            target_album_id = getattr(enhanced_dto, "album_id", None)
            if target_album_id:
                if session.query(Album.id).filter_by(id=target_album_id).first():
                    current_track.album_id = target_album_id
                else:
                    logger.warning(
                        "Target album_id %s does not exist in DB during in-place track hydration; verifying existing album_id",
                        target_album_id,
                    )
                    if current_track.album_id and not session.query(Album.id).filter_by(id=current_track.album_id).first():
                        current_track.album_id = None
            elif current_track.album_id and not session.query(Album.id).filter_by(id=current_track.album_id).first():
                current_track.album_id = None
            return current_track

        return None

    reconcile_media_for_track = reconcile_media_assignment


def reconcile_media_assignment(
    session: Session,
    media: "LocalMedia",
    enhanced_dto: EchosyncTrack,
    current_chromaprint: str | None = None,
) -> Track:
    """Convenience functional wrapper for ResolutionAdapter.reconcile_media_assignment."""
    return ResolutionAdapter().reconcile_media_assignment(session, media, enhanced_dto, current_chromaprint)


reconcile_media_for_track = reconcile_media_assignment


def prune_orphaned_track_if_empty(session: Session, track_id: int | None) -> bool:
    """Convenience functional wrapper for ResolutionAdapter.prune_orphaned_track_if_empty."""
    return ResolutionAdapter().prune_orphaned_track_if_empty(session, track_id)
