with open('/app/services/download_manager.py', 'r') as f:
    content = f.read()

import re

# Hook queue_download
new_queue_download = """    def queue_download(self, track: EchosyncTrack, quality_profile_id: Optional[str] = None) -> int:
        from core.hook_manager import hook_manager
        hook_result = hook_manager.apply_filters('ON_DOWNLOAD_MANAGER_QUEUE', {'skip': False, 'result': None}, track=track, quality_profile_id=quality_profile_id)
        if hook_result and isinstance(hook_result, dict) and hook_result.get('skip'):
            return hook_result.get('result')

        logger.info(f"Queueing download for track {track.id}")"""

content = re.sub(
    r'    def queue_download\(self, track: EchosyncTrack, quality_profile_id: Optional\[str\] = None\) -> int:\n        logger\.info\(f"Queueing download for track {track\.id}"\)',
    new_queue_download,
    content,
    flags=re.DOTALL
)

with open('/app/services/download_manager.py', 'w') as f:
    f.write(content)

with open('/app/services/media_manager.py', 'r') as f:
    content = f.read()

# Add a top-level skip hook to get_track_stream
new_get_track_stream = """    def get_track_stream(self, track_id: int) -> Optional[str]:
        from core.hook_manager import hook_manager
        hook_result = hook_manager.apply_filters('ON_MEDIA_MANAGER_STREAM', {'skip': False, 'result': None}, track_id=track_id)
        if hook_result and isinstance(hook_result, dict) and hook_result.get('skip'):
            return hook_result.get('result')

        # Retrieve the track"""

content = re.sub(
    r'    def get_track_stream\(self, track_id: int\) -> Optional\[str\]:\n        # Retrieve the track',
    new_get_track_stream,
    content,
    flags=re.DOTALL
)

with open('/app/services/media_manager.py', 'w') as f:
    f.write(content)
