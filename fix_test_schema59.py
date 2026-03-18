with open("tests/services/test_download_logic.py", "r") as f:
    code = f.read()

# Replace test_process_queue_skips_failed_terminal with await manager._process_loop() since it was already an async method in some old version, but it is synchronous in download_manager.py right now
code = code.replace("await self.manager._process_loop()", "self.manager._process_loop()")

# Let's fix the patching once more for ALL mock usages
code = code.replace("mock_get_work_db.return_value = mock_get_work_db_fixture.return_value", "mock_get_work_db.return_value = mock_get_work_db_fixture")
code = code.replace("with mock_get_work_db_fixture.return_value.session_scope() as session:", "with mock_get_work_db_fixture.session_scope() as session:")

with open("tests/services/test_download_logic.py", "w") as f:
    f.write(code)
