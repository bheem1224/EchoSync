import time
import pytest
from unittest.mock import patch, MagicMock, ANY

from core.task_manager import (
    job_queue,
    JobQueue,
    TaskCategory,
    TaskState,
    ScheduledJob,
    plugin_state_manager,
    PluginLifecycleState,
    supervisor,
    ProcessOwner,
    OwnerType,
)
from core.nexus_framework.plugin_loader import PluginRegistry, PluginBase


def test_task_queue_gating_initializing_and_error(monkeypatch):
    """Verify jobs linked to a plugin in INITIALIZING or ERROR state are blocked and deferred."""
    test_queue = JobQueue(poll_interval=0.1)
    plugin_id = "plugin.test_gating"

    executed = []
    def dummy_task():
        executed.append(True)

    test_queue.register_job(
        name="test_gated_job",
        func=dummy_task,
        interval_seconds=1.0,
        start_after=0.0,
        plugin=plugin_id
    )

    # 1. State INITIALIZING -> can_execute returns False, state set to PENDING_BLOCKED
    plugin_state_manager.set_state(plugin_id, PluginLifecycleState.INITIALIZING, "Loading dependencies")
    job = test_queue._jobs["test_gated_job"]
    
    assert not test_queue.can_execute(job)
    assert job.state == TaskState.PENDING_BLOCKED
    assert job.next_run > time.time() + 5.0  # Deferred by 10 seconds

    # 2. State ERROR -> can_execute returns False
    plugin_state_manager.set_state(plugin_id, PluginLifecycleState.ERROR, "Fatal crash")
    assert not test_queue.can_execute(job)
    assert job.state == TaskState.PENDING_BLOCKED

    # 3. State READY -> can_execute returns True
    plugin_state_manager.set_state(plugin_id, PluginLifecycleState.READY, "Service ready")
    assert test_queue.can_execute(job)


def test_task_queue_log_damping(caplog):
    """Verify warning log is emitted ONLY on state transition into PENDING_BLOCKED."""
    test_queue = JobQueue()
    plugin_id = "plugin.log_damp_test"

    test_queue.register_job(
        name="damp_job",
        func=lambda: None,
        interval_seconds=1.0,
        plugin=plugin_id
    )
    job = test_queue._jobs["damp_job"]
    plugin_state_manager.set_state(plugin_id, PluginLifecycleState.ERROR, "Gating error")

    # First call -> state transitions from PENDING to PENDING_BLOCKED (logs warning)
    job.state = TaskState.PENDING
    with patch("core.task_manager.task_queue.logger.warning") as mock_warn:
        res1 = test_queue.can_execute(job)
        assert not res1
        assert mock_warn.call_count == 1

    # Second call -> state is ALREADY PENDING_BLOCKED (log is suppressed/damped)
    with patch("core.task_manager.task_queue.logger.warning") as mock_warn:
        res2 = test_queue.can_execute(job)
        assert not res2
        assert mock_warn.call_count == 0


def test_disable_plugin_terminates_supervisor_processes():
    """Verify disabling a plugin terminates its registered PIDs in ProcessSupervisor."""
    class DummyPlugin(PluginBase):
        name = "EchoSync.DummyGating"

    plugin_id_str = "echosync.dummygating"
    PluginRegistry.register(DummyPlugin, name=plugin_id_str, source_type="community")

    # Register process PIDs under the plugin
    owner = ProcessOwner(
        owner_id=plugin_id_str,
        owner_type=OwnerType.PLUGIN,
        pid=8888,
        task_name="dummy_process"
    )
    reg_id = supervisor.register_process(owner)
    assert len(supervisor.get_active_processes(plugin_id_str)) == 1

    with patch("os.kill") as mock_kill:
        disabled = PluginRegistry.disable_plugin(plugin_id_str)
        assert disabled
        mock_kill.assert_called_with(8888, ANY)

    # Process should be terminated/unregistered and plugin state UNCONFIGURED
    assert len(supervisor.get_active_processes(plugin_id_str)) == 0
    status = plugin_state_manager.get_state(plugin_id_str)
    assert status.state == PluginLifecycleState.UNCONFIGURED
