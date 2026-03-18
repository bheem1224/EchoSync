import re
with open("tests/conftest.py", "r") as f:
    code = f.read()

# Make the mock_work_db fixture ACTUALLY return the WorkingDatabase and not a MagicMock!
# There is still a mock_get_work_db_fixture lingering? NO, it's just `mock_work_db` now. But earlier I wrote:
# "mock = MagicMock()\n    mock.return_value = work_db\n    yield mock" in my patch. Let's fix!
pattern = re.compile(r'@pytest.fixture\ndef mock_work_db\(tmp_path\):.*?work_db\.dispose\(\)', re.DOTALL)
new_fixture = """@pytest.fixture
def mock_work_db(tmp_path):
    from database.working_database import WorkingDatabase
    db_path = tmp_path / "working.db"
    work_db = WorkingDatabase(str(db_path))
    work_db.create_all()
    yield work_db
    work_db.dispose()"""

code = pattern.sub(new_fixture, code)

with open("tests/conftest.py", "w") as f:
    f.write(code)
