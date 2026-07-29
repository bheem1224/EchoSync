import sys
from core.task_manager import health_service as _mod
sys.modules[__name__] = _mod
