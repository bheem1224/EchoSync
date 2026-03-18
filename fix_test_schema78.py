with open("services/download_manager.py", "r") as f:
    code = f.read()

# I found the issue! In `_cleanup_queue_against_library` it uses `self.work_db.session_scope` BUT it ALSO queries `Track` inside that session!
# `existing = session.query(Track).filter(...)` where `session` is `work_db`!
# `Track` belongs to `MusicDatabase` and the `tracks` table doesn't exist in `working.db`.
code = code.replace("existing = session.query(Track).filter(", "db = get_database()\n                        with db.session_scope() as music_session:\n                            existing = music_session.query(Track).filter(")
code = code.replace(").first()\n                        \n                        if existing:", ").first()\n                        \n                            if existing:\n                                session.delete(item)")

# Wait, `_purge_existing_tracks_from_queue` also has this bug!
# It queries `Track` inside `self.work_db.session_scope()`
# 1141: exists = session.query(session.query(Track).join(Artist).filter(*filters).exists()).scalar()
# Let's fix that!
