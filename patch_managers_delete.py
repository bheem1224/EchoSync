with open('/app/services/media_manager.py', 'r') as f:
    content = f.read()

import re

# Add skip hook to delete_track
new_delete_track = """    def delete_track(self, track_id: int) -> bool:
        from core.hook_manager import hook_manager
        hook_result = hook_manager.apply_filters('ON_MEDIA_MANAGER_DELETE', {'skip': False, 'result': None}, track_id=track_id)
        if hook_result and isinstance(hook_result, dict) and hook_result.get('skip'):
            return hook_result.get('result')

        # Requires a session scope to delete"""

content = re.sub(
    r'    def delete_track\(self, track_id: int\) -> bool:\n        # Requires a session scope to delete',
    new_delete_track,
    content,
    flags=re.DOTALL
)

with open('/app/services/media_manager.py', 'w') as f:
    f.write(content)
