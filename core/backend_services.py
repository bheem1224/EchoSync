import sys

from core.task_manager import backend_services as _mod

sys.modules[__name__] = _mod
