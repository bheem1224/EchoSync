# Ah, I replaced `check_track_exists` earlier, but maybe it isn't in `_track_exists_in_library` anymore?
# Let's check `services/download_manager.py` for ANY reference to `db.check_track_exists` or `db_track`.
# Wait, I changed `_track_exists_in_library` to NOT use `check_track_exists` a LONG time ago!
# Wait! In the error message:
# WARNING  download_manager:download_manager.py:1151 Error checking queued item 1: (sqlite3.OperationalError) no such table: tracks
# [SQL: SELECT EXISTS (SELECT 1
# FROM tracks JOIN artists ON artists.id = tracks.artist_id
# WHERE lower(artists.name) LIKE lower(?) AND lower(tracks.title) LIKE lower(?) AND (EXISTS (SELECT 1
# FROM albums
# WHERE albums.id = tracks.album_id AND lower(albums.title) LIKE lower(?)))) AS anon_1]
# This SQL looks like `session.query(Track).filter(...)`!
# This is EXACTLY what `_track_exists_in_library` does!
# AND where is it getting executed?
# `with self.db.session_scope() as session:`!
# BUT the query is executing against a database that has no `tracks` table!
# That means `self.db` is ACTUALLY `self.work_db` or a new memory DB!
# Let's look at how I set `self.db = mock_db` in `test_startup_purge_removes_existing`.
