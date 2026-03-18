with open("services/download_manager.py", "r") as f:
    code = f.read()

# Ah! `_purge_existing_tracks_from_queue()` loops over `queued_items` and calls:
# `self._track_exists_in_library(...)`
# So where is the `no such table: tracks` coming from?
# `self._track_exists_in_library` does: `with self.db.session_scope() as session:`
# But earlier I modified `DownloadManager.__init__` to load `self.db = get_database()` and `self.work_db = get_working_database()`
# Is `_purge_existing_tracks_from_queue` running on a separate thread or instantiated object? No!
# BUT WAIT.
# Look at `check_track_exists` in `database/music_database.py`!
