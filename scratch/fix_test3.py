import re

content = open("tests/plugins/test_slskd_webhooks.py").read()
content = content.replace(
    "DownloadManager._instance = None",
    'DownloadManager._instance = None\n        from plugins.EchoSync.slskd.plugin import on_webhook_received\n        sdk._WEBHOOK_HANDLERS.setdefault(sdk.compute_plugin_crc32("EchoSync.slskd"), []).append(on_webhook_received)',
)
open("tests/plugins/test_slskd_webhooks.py", "w").write(content)
