from datetime import datetime, timezone
import threading
from typing import Dict
from core.tiered_logger import get_logger
from core.task_manager.models import PluginLifecycleState, PluginStatus

logger = get_logger("plugin_state_manager")


class PluginStateManager:
    """
    Manages dynamic lifecycle state tracking and capability gating for plugins.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._states: Dict[str, PluginStatus] = {}

    def set_state(self, plugin_id: str, state: PluginLifecycleState, message: str = "") -> None:
        """
        Updates the lifecycle state of a plugin and logs state transitions.

        Args:
            plugin_id: Unique identifier for the plugin (e.g. 'plugin.plex' or 'echosync.local_server').
            state: Target PluginLifecycleState.
            message: Optional detail message explaining the transition or error.
        """
        now = datetime.now(timezone.utc)
        with self._lock:
            old_status = self._states.get(plugin_id)
            old_state = old_status.state if old_status else PluginLifecycleState.UNCONFIGURED

            new_status = PluginStatus(
                state=state,
                message=message,
                last_health_check=now
            )
            self._states[plugin_id] = new_status

        if old_state != state:
            logger.info(
                f"Plugin '{plugin_id}' state transition: {old_state.value.upper()} -> {state.value.upper()}"
                + (f" ({message})" if message else "")
            )
        else:
            logger.debug(f"Plugin '{plugin_id}' state updated: {state.value.upper()}")

    def get_state(self, plugin_id: str) -> PluginStatus:
        """
        Fetches current status for a given plugin. Defaults to UNCONFIGURED.

        Args:
            plugin_id: Unique identifier for the plugin.

        Returns:
            PluginStatus: Current status object.
        """
        with self._lock:
            status = self._states.get(plugin_id)
            if not status:
                return PluginStatus(
                    state=PluginLifecycleState.UNCONFIGURED,
                    message="Plugin state not initialized",
                    last_health_check=None
                )
            return status

    def can_accept_work(self, plugin_id: str) -> bool:
        """
        Capability gate: Returns True ONLY if state is READY or DEGRADED.
        Returns False for UNCONFIGURED, INITIALIZING, or ERROR.

        Args:
            plugin_id: Unique identifier for the plugin.

        Returns:
            bool: Whether the plugin is capable of processing requests.
        """
        status = self.get_state(plugin_id)
        return status.state in (PluginLifecycleState.READY, PluginLifecycleState.DEGRADED)


# Global PluginStateManager singleton
plugin_state_manager = PluginStateManager()
