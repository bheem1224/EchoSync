import subprocess
import os

print("Testing core files syntax...")
files = [
    '/app/core/plugin_loader.py',
    '/app/core/binary_runner.py',
    '/app/database/working_database.py',
    '/app/database/music_database.py',
    '/app/database/config_database.py',
    '/app/core/plugin_router.py',
    '/app/web/api_app.py',
    '/app/core/job_queue.py',
    '/app/core/matching_engine/matching_engine.py',
    '/app/services/download_manager.py',
    '/app/services/media_manager.py'
]

for f in files:
    subprocess.run(['python', '-m', 'py_compile', f], check=True)

print("Syntax check passed.")
