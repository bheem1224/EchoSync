with open("tests/conftest.py", "r") as f:
    code = f.read()

# Fix mock_get_work_db fixture to NOT return a MagicMock wrapper around the WorkingDatabase!
new = """
@pytest.fixture
def mock_get_work_db(tmp_path):
    from database.working_database import WorkingDatabase
    db_path = tmp_path / "working.db"
    work_db = WorkingDatabase(str(db_path))
    work_db.create_all()
    # We yield a MagicMock that returns work_db when called
    from unittest.mock import MagicMock
    mock = MagicMock()
    mock.return_value = work_db
    yield mock
    work_db.dispose()

@pytest.fixture
def mock_db(tmp_path):
    from database.music_database import MusicDatabase
    db_path = tmp_path / "music.db"
    db = MusicDatabase(str(db_path))
    db.create_all()
    yield db
    db.dispose()
"""
code += new
with open("tests/conftest.py", "w") as f:
    f.write(code)
