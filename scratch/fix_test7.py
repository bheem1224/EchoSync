import re

content = open("tests/plugins/test_slskd_webhooks.py").read()
content = content.replace(
    'with patch(\n        "database.working_database.get_working_database", return_value=mock_work_db\n    ):',
    """with patch(
        "database.working_database.get_working_database", return_value=mock_work_db
    ), patch(
        "web.routes.webhooks.lookup_registered_endpoint", return_value={"secret": secret}
    ):""",
)
open("tests/plugins/test_slskd_webhooks.py", "w").write(content)
