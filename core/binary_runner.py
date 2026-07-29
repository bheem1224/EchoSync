import sys
from core.task_manager import binary_runner as _mod
sys.modules[__name__] = _mod
