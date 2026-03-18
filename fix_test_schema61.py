with open("tests/conftest.py", "r") as f:
    code = f.read()

# I am completely nuking the broken `mock_get_work_db_fixture` and returning it to the name `mock_work_db`.
code = code.replace("def mock_get_work_db_fixture(tmp_path):", "def mock_work_db(tmp_path):")

# Remove the bad MagicMock wrapper
old = """
    # Return a mock whose return_value is work_db (this matches exactly what @patch does!)
    from unittest.mock import MagicMock
    mock = MagicMock()
    mock.return_value = work_db
    yield mock
"""
new = """
    yield work_db
"""
code = code.replace(old, new)

with open("tests/conftest.py", "w") as f:
    f.write(code)


with open("tests/services/test_download_logic.py", "r") as f:
    code = f.read()

# Swap `mock_get_work_db_fixture` back to `mock_work_db` in tests
code = code.replace("mock_get_work_db_fixture", "mock_work_db")

with open("tests/services/test_download_logic.py", "w") as f:
    f.write(code)
