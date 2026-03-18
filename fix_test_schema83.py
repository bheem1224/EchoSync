with open("tests/services/test_download_logic.py", "r") as f:
    code = f.read()

# I forgot to import Album.
code = code.replace("from database.music_database import Track, Artist, MusicDatabase", "from database.music_database import Track, Artist, Album, MusicDatabase")
with open("tests/services/test_download_logic.py", "w") as f:
    f.write(code)
