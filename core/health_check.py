import sys

from core.task_manager import health as _mod

sys.modules[__name__] = _mod
