from unittest.mock import patch

from web.api_app import create_app

with patch(
    "core.nexus_framework.plugin_loader.PluginRegistry.set_disabled_plugins",
    lambda disabled: None,
):
    app = create_app(testing=True)
    for rule in app.url_map.iter_rules():
        if "callback" in rule.rule or "spotify" in rule.rule:
            print(rule.rule)
