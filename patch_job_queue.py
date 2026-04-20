with open('/app/core/job_queue.py', 'r') as f:
    content = f.read()

import re

# Add register_scheduled_task(name, func, frequency)
new_method = """def register_scheduled_task(name: str, func: Callable[[], Any], frequency: float):
    \"\"\"SDK Helper to expose internal scheduler to plugins easily.\"\"\"
    job_queue.register_job(name=name, func=func, interval_seconds=frequency)

def register_job(**kwargs):"""

content = content.replace("def register_job(**kwargs):", new_method)

with open('/app/core/job_queue.py', 'w') as f:
    f.write(content)
