with open('/app/web/api_app.py', 'r') as f:
    content = f.read()

import re

# Add the new plugin router registry blueprints to the flask app
# after loading the dynamic blueprints from the loader.

new_plugin_router_loading = """    # Register Dynamic Blueprints from Providers/Plugins
    for bp in loader.get_all_blueprints():
        try:
            app.register_blueprint(bp)
        except Exception as e:
            print(f"[ERROR] Failed to register blueprint {bp.name}: {e}")

    # Register explicitly mounted Plugin SDK Routers
    from core.plugin_router import PluginRouterRegistry
    for bp in PluginRouterRegistry.get_all_routers():
        try:
            app.register_blueprint(bp)
        except Exception as e:
            print(f"[ERROR] Failed to register SDK router {bp.name}: {e}")"""

content = content.replace(
    """    # Register Dynamic Blueprints from Providers/Plugins
    for bp in loader.get_all_blueprints():
        try:
            app.register_blueprint(bp)
        except Exception as e:
            print(f"[ERROR] Failed to register blueprint {bp.name}: {e}")""",
    new_plugin_router_loading
)

with open('/app/web/api_app.py', 'w') as f:
    f.write(content)
