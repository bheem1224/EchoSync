with open('web/api_app.py', 'r') as f:
    content = f.read()

orig_return = """        try:
            get_database().engine.dispose(close=False)
        except Exception:
            pass

    return app"""

patch_return = """        try:
            get_database().engine.dispose(close=False)
        except Exception:
            pass

    import atexit
    def on_shutdown():
        from core.hook_manager import hook_manager
        try:
            hook_manager.apply_filters('ON_SYSTEM_SHUTDOWN', None)
        except Exception:
            pass
    atexit.register(on_shutdown)

    return app"""

content = content.replace(orig_return, patch_return)

with open('web/api_app.py', 'w') as f:
    f.write(content)
