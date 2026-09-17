import sys

from core.task_manager import backend_services as _mod
from core.task_manager.backend_services import start_services

sys.modules[__name__] = _mod

__all__ = ["start_services"]
