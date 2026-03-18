with open("tests/services/test_download_logic.py", "r") as f:
    code = f.read()

# Replace manager._process_loop with await manager._process_loop? No, wait!
# We just need to fix `_track_exists_in_library` failing because it uses `self.work_db.session_scope` where it should be `self.db.session_scope`!
# Wait! In `fix_test_schema62.py` I REPLACED it back to `self.db`.
# Let's check `services/download_manager.py` to see what `_track_exists_in_library` uses.
