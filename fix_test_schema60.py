with open("tests/services/test_download_logic.py", "r") as f:
    code = f.read()

# Replace mock_get_work_db_fixture argument name back to mock_work_db
code = code.replace("mock_get_work_db_fixture", "mock_work_db")

with open("tests/services/test_download_logic.py", "w") as f:
    f.write(code)
