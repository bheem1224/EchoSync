import sys

from core.task_manager import task_queue as _mod

sys.modules[__name__] = _mod
