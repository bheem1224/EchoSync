import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from database.music_database import get_database, Track, Artist, AudioFingerprint
from core.file_handling.path_mapper import PathMapper
from sqlalchemy import or_, and_, func, Integer

# Pass absolute path directly
db_path = "C:\\Users\\bheem\\Nextcloud2\\VS-Code-Projects\\EchoSync\\data\\music_library.db"
db = get_database(db_path)
print("Music Database Path:", db.database_path)

with db.session_scope() as session:
    total_tracks = session.query(Track).count()
    print("Total tracks in DB:", total_tracks)

    _va_artist_ids_subq = (
        session.query(Artist.id)
        .filter(Artist.name.ilike('various artist%'))
    )
    va_count = session.query(Track).filter(Track.artist_id.in_(_va_artist_ids_subq)).count()
    print("Total Various Artist tracks:", va_count)

    # Let's count how many match each of the conditions in the enhancer query
    needs_id_count = session.query(Track).filter(or_(
        Track.musicbrainz_id.is_(None),
        and_(
            Track.musicbrainz_id == "NOT_FOUND",
            func.coalesce(
                func.json_extract(Track.metadata_status, '$.enhancement_attempts'),
                0,
            ).cast(Integer) < 5,
        ),
    )).count()
    print("Needs identification count:", needs_id_count)

    cjk_count = session.query(Track).filter(
        and_(
            Track.musicbrainz_id.isnot(None),
            Track.musicbrainz_id != "NOT_FOUND",
            func.json_extract(Track.metadata_status, '$.cjk_restored').is_(None),
        )
    ).count()
    print("Missing cjk_restored count:", cjk_count)

    va_unfixed_count = session.query(Track).filter(
        and_(
            Track.artist_id.in_(_va_artist_ids_subq),
            func.json_extract(
                Track.metadata_status, '$.artist_fixed_from_tags'
            ).is_(None),
        )
    ).count()
    print("Various Artist unfixed count:", va_unfixed_count)

    # Let's get the first 10 tracks that would be processed
    required_keys = ['cjk_restored']
    needs_identification = or_(
        Track.musicbrainz_id.is_(None),
        and_(
            Track.musicbrainz_id == "NOT_FOUND",
            func.coalesce(
                func.json_extract(Track.metadata_status, '$.enhancement_attempts'),
                0,
            ).cast(Integer) < 5,
        ),
    )
    conditions = [needs_identification]
    for key in required_keys:
        conditions.append(
            and_(
                Track.musicbrainz_id.isnot(None),
                Track.musicbrainz_id != "NOT_FOUND",
                func.json_extract(Track.metadata_status, f'$.{key}').is_(None),
            )
        )
    conditions.append(
        and_(
            Track.artist_id.in_(_va_artist_ids_subq),
            func.json_extract(
                Track.metadata_status, '$.artist_fixed_from_tags'
            ).is_(None),
        )
    )

    tracks = session.query(Track).filter(or_(*conditions)).limit(10).all()
    print(f"\nFirst 10 tracks matching the query:")
    for t in tracks:
        local_path_str = PathMapper.to_local(t.file_path)
        exists = Path(local_path_str).exists()
        print(f"ID: {t.id} | Path: {t.file_path} | Local Path: {local_path_str} | Exists: {exists} | MBID: {t.musicbrainz_id} | Status: {t.metadata_status}")
