# For testing `_track_exists_in_library`, it uses `self.db` which is `manager.db` which is `mock_db`
# And `session.query(Track).join(Artist)`
# WHY IS IT RETURNING FALSE AND CAUSING `assert 1 == 0`?
# In `services/download_manager.py`:
# filters = [Artist.name.ilike(artist_name.strip()), Track.title.ilike(title.strip())]
# In the test, `artist_name="The Artist"`, `title="Track A"`.
# The test sets `artist = Artist(name="The Artist")`, `track = Track(title="Track A", artist=artist)`
# The filter SHOULD work!
# Let's manually run the query in the test and print it.
