# Error checking queued item 1: (sqlite3.OperationalError) no such table: tracks
# Why? Because in `_track_exists_in_library` it uses `self.db`, but wait!
# `_track_exists_in_library` does `with self.db.session_scope() as session:` which is correct.
# BUT why did `session.query(Track)` look for `tracks` in `working.db`?
# Oh! `self.db` was replaced with `self.work_db` in `_track_exists_in_library` by my mass replacement script!
with open("services/download_manager.py", "r") as f:
    code = f.read()

code = code.replace("def _track_exists_in_library(self, artist_name: str, title: str, album: Optional[str] = None, duration: Optional[int] = None) -> bool:\n        \"\"\"\n        Check if a track already exists in the library (database).\n\n        Args:\n            artist_name: Artist name\n            title: Track title\n\n        Returns:\n            True if track exists, False otherwise\n        \"\"\"\n        if not artist_name or not title:\n            return False\n\n        try:\n            with self.work_db.session_scope() as session:", "def _track_exists_in_library(self, artist_name: str, title: str, album: Optional[str] = None, duration: Optional[int] = None) -> bool:\n        \"\"\"\n        Check if a track already exists in the library (database).\n\n        Args:\n            artist_name: Artist name\n            title: Track title\n\n        Returns:\n            True if track exists, False otherwise\n        \"\"\"\n        if not artist_name or not title:\n            return False\n\n        try:\n            with self.db.session_scope() as session:")

with open("services/download_manager.py", "w") as f:
    f.write(code)
