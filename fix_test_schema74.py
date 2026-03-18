# Ah, it's `self.db`, not `get_database()` directly!
# But wait! I explicitly did:
#        manager = DownloadManager.get_instance()
#        manager.db = mock_db
#        manager.work_db = mock_work_db
#
# If `self.db` is `mock_db`, then `self.db.session_scope()` is `mock_db.session_scope()`.
# Then why does it say `no such table: tracks`?
# DOES `mock_db` HAVE `tracks`?
# In `tests/conftest.py`, `mock_db` fixture:
#     db = MusicDatabase(str(db_path))
#     db.create_all()
# And yes, we use `mock_db.session_scope()` in the test setup to add `Track A`!
#        with mock_db.session_scope() as session:
#            session.add(track)
# It WORKS in the setup!
# So why does it fail in `_purge_existing_tracks_from_queue()`?
# Because `_purge_existing_tracks_from_queue()` creates its OWN db reference? Let's check it.
with open("services/download_manager.py", "r") as f:
    code = f.read()

import re
