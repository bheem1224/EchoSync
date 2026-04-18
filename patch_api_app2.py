with open('web/api_app.py', 'r') as f:
    content = f.read()

# I used hook_manager.apply_filters but the user specifically said:
# wrap `hook_manager.trigger('ON_SYSTEM_SHUTDOWN', None)` in a `try/except`
# Wait, let me check what the user said in the prompt:
# "wrap `hook_manager.trigger('ON_SYSTEM_SHUTDOWN', None)` in a `try/except`"

# I should probably just replace it with what they asked. But wait, earlier I checked `hook_manager.py` and it doesn't have a `trigger` method. It has `apply_filters`.
# Maybe `apply_filters` is right, maybe I should just create a `.trigger()` alias.
# If I look closely at the prompt:
# "Task 5: Inject ON_SYSTEM_SHUTDOWN Hook (MEDIUM) Action: Plugins need a way to cleanly close external connections when the app stops. Import the atexit module. Create a shutdown function that wraps hook_manager.trigger('ON_SYSTEM_SHUTDOWN', None) in a try/except, and register it using atexit.register()."
# I will just write what they requested, even if it might raise an error, or wait, I can just use `apply_filters` because it's the actual method name. I'll stick to what the user said just in case. Wait, if it doesn't exist, it will throw an AttributeError. Is `trigger` a real method? Let's verify `hook_manager.py` again.
