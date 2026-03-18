# Wait, now that I look at `test_queue_download_skips_existing`:
# `track_to_download = SoulSyncTrack(raw_title="Track A", artist_name="The Artist", album_title="Some Album")`
# AND the track in the library is:
# `Track(title="Track A", artist=artist, file_path="/music...")`
# The problem is that the filter uses:
# filters.append(Track.album.has(Album.title.ilike(album.strip())))
# BUT the track in the test DOES NOT HAVE AN ALBUM SET!
# But the download requests has an `album_title="Some Album"`.
# So `_track_exists_in_library` filters by album and returns False!
# Let's fix the test by giving the track an album! Or setting album_title="" in the download request!

with open("tests/services/test_download_logic.py", "r") as f:
    code = f.read()

code = code.replace("track = Track(\n                title=\"Track A\",\n                artist=artist,\n                file_path=\"/music/The Artist/Track A.mp3\"\n            )\n            session.add(track)", "album = Album(title=\"Some Album\", artist=artist)\n            session.add(album)\n            track = Track(\n                title=\"Track A\",\n                artist=artist,\n                album=album,\n                file_path=\"/music/The Artist/Track A.mp3\"\n            )\n            session.add(track)")
code = code.replace("track = Track(\n                title=\"Track B\",\n                artist=artist,\n                file_path=\"/music/The Artist/Track B.mp3\"\n            )\n            session.add(track)", "album = Album(title=\"Some Album\", artist=artist)\n            session.add(album)\n            track = Track(\n                title=\"Track B\",\n                artist=artist,\n                album=album,\n                file_path=\"/music/The Artist/Track B.mp3\"\n            )\n            session.add(track)")
with open("tests/services/test_download_logic.py", "w") as f:
    f.write(code)
