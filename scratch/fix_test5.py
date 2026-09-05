import re

content = open("tests/plugins/test_slskd_webhooks.py").read()
content = content.replace(
    '        with patch(\n            "services.download_manager.get_working_database", return_value=mock_work_db\n        ):',
    """        from plugins.EchoSync.slskd.plugin import on_webhook_received
        sdk._WEBHOOK_HANDLERS.setdefault(sdk.compute_plugin_crc32("EchoSync.slskd"), []).append(on_webhook_received)
        with patch(
            "database.working_database.get_working_database", return_value=mock_work_db
        ):""",
)
content = content.replace(
    "# Verify state transitioned to VERIFYING",
    "import time\n        time.sleep(0.1)\n        # Verify state transitioned to VERIFYING",
)
open("tests/plugins/test_slskd_webhooks.py", "w").write(content)
