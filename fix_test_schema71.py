with open("services/download_manager.py", "r") as f:
    code = f.read()

# I am replacing `self.work_db` with `self.db` in `_track_exists_in_library` because `check_track_exists` logic requires `MusicDatabase`!
# Ah! I already replaced it! Let's check!
