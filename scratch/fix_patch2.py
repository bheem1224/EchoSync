import re

content = open("tests/plugins/test_slskd_webhooks.py").read()
content = content.replace(
    'patch(\n        "plugins.EchoSync.slskd.plugin.get_working_database", return_value=mock_work_db\n    )',
    'patch(\n        "database.working_database.get_working_database", return_value=mock_work_db\n    )',
)
open("tests/plugins/test_slskd_webhooks.py", "w").write(content)
