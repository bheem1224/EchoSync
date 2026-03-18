import re
with open("tests/services/test_download_logic.py", "r") as f:
    code = f.read()

# I had reverted the test file earlier which reintroduced old mock arguments that are now failing. Let's fix those names again!
code = code.replace("mock_work_db", "mock_get_work_db_fixture")
with open("tests/services/test_download_logic.py", "w") as f:
    f.write(code)
