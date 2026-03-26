"""
Backward-compatibility shim.

core/storage.py was relocated to core/file_handling/storage.py in v2.2.0.
All existing `from core.storage import X` calls continue to work through
this re-export module.  New code should import directly from the new path:

    from core.file_handling.storage import StorageService, get_storage_service
"""

from core.file_handling.storage import *          # noqa: F401, F403
from core.file_handling.storage import (          # noqa: F401  (explicit for IDEs)
    StorageService,
    get_storage_service,
)
