with open("services/download_manager.py", "r") as f:
    code = f.read()

# I am fixing `_track_exists_in_library` to use `self.db` properly so we can mock it in tests.
code = code.replace("db = get_database()\n            with db.session_scope() as session:", "with self.db.session_scope() as session:")

with open("services/download_manager.py", "w") as f:
    f.write(code)
