# Wait, `check_track_exists` in `MusicDatabase` has:
#        with self.session_scope() as session:
#            # Find candidates
#            candidates = session.query(Track).join(Artist)...
# This should work! `self.session_scope` uses `self.SessionLocal()`.
# Why `no such table: tracks`?
# Is `self` in `check_track_exists` the correct `MusicDatabase` instance?
# `self._track_exists_in_library` calls:
#    db = get_database()
#    db_track, confidence = db.check_track_exists(...)
# YES!! IT CALLS `db = get_database()` instead of `self.db`!!!
# Let's check `_track_exists_in_library` in `services/download_manager.py` again.
