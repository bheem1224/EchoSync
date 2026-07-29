import sys
from core.task_manager import system_jobs as _mod
sys.modules[__name__] = _mod
