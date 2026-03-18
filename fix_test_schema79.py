with open("services/download_manager.py", "r") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "                        exists = session.query(" in line and "session.query(Track).join(Artist)" in lines[i+1]:
        lines[i] = "                        db = get_database()\n                        with db.session_scope() as music_session:\n                            exists = music_session.query(\n                                music_session.query(Track).join(Artist).filter(*filters).exists()\n                            ).scalar()\n"
        lines[i+1] = ""
        lines[i+2] = ""

# I also need to fix _cleanup_queue_against_library
for i, line in enumerate(lines):
    if "                        db = get_database()" in line and "with db.session_scope() as music_session:" in lines[i+1] and "existing = music_session.query(Track).filter(" in lines[i+2]:
        pass # Already fixed via string replace earlier! Let's check!

with open("services/download_manager.py", "w") as f:
    f.writelines(lines)
