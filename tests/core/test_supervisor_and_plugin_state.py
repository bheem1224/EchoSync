from unittest.mock import ANY, MagicMock, patch

from core.task_manager import (
    CoreBinaryRunner,
    OwnerType,
    PluginLifecycleState,
    ProcessOwner,
    plugin_state_manager,
    supervisor,
)


def test_supervisor_register_and_unregister():
    """Verify process registration, querying, and unregistration."""
    owner = ProcessOwner(
        owner_id="plugin.plex",
        owner_type=OwnerType.PLUGIN,
        pid=1234,
        task_name="media_scan",
        metadata={"target": "library_1"},
    )

    reg_id = supervisor.register_process(owner)
    assert reg_id is not None
    assert reg_id.startswith("plugin.plex_")

    active = supervisor.get_active_processes("plugin.plex")
    assert len(active) == 1
    assert active[0].owner_id == "plugin.plex"
    assert active[0].pid == 1234
    assert active[0].task_name == "media_scan"

    # All active processes
    all_active = supervisor.get_active_processes()
    assert any(p.pid == 1234 for p in all_active)

    # Unregister
    supervisor.unregister_process(reg_id)
    assert len(supervisor.get_active_processes("plugin.plex")) == 0


def test_supervisor_terminate_owner_processes():
    """Verify process termination signal dispatching."""
    owner1 = ProcessOwner(
        owner_id="plugin.spotify",
        owner_type=OwnerType.PLUGIN,
        pid=9999,
        task_name="sync_loop",
    )
    owner2 = ProcessOwner(
        owner_id="plugin.spotify",
        owner_type=OwnerType.PLUGIN,
        pid=9998,
        task_name="download_worker",
    )

    reg1 = supervisor.register_process(owner1)
    reg2 = supervisor.register_process(owner2)

    assert len(supervisor.get_active_processes("plugin.spotify")) == 2

    with patch("os.kill") as mock_kill:
        supervisor.terminate_owner_processes("plugin.spotify")
        assert mock_kill.call_count == 2
        mock_kill.assert_any_call(9999, ANY)
        mock_kill.assert_any_call(9998, ANY)

    assert len(supervisor.get_active_processes("plugin.spotify")) == 0


def test_plugin_state_manager_transitions_and_gating():
    """Verify plugin lifecycle state transitions and work acceptance gating."""
    plugin_id = "echosync.test_plugin"

    # Default state is UNCONFIGURED
    status = plugin_state_manager.get_state(plugin_id)
    assert status.state == PluginLifecycleState.UNCONFIGURED
    assert not plugin_state_manager.can_accept_work(plugin_id)

    # INITIALIZING state
    plugin_state_manager.set_state(
        plugin_id, PluginLifecycleState.INITIALIZING, "Loading dependencies"
    )
    status = plugin_state_manager.get_state(plugin_id)
    assert status.state == PluginLifecycleState.INITIALIZING
    assert status.message == "Loading dependencies"
    assert status.last_health_check is not None
    assert not plugin_state_manager.can_accept_work(plugin_id)

    # READY state -> can_accept_work is True
    plugin_state_manager.set_state(
        plugin_id, PluginLifecycleState.READY, "Service operational"
    )
    status = plugin_state_manager.get_state(plugin_id)
    assert status.state == PluginLifecycleState.READY
    assert plugin_state_manager.can_accept_work(plugin_id)

    # DEGRADED state -> can_accept_work is True
    plugin_state_manager.set_state(
        plugin_id, PluginLifecycleState.DEGRADED, "Rate limit reached"
    )
    status = plugin_state_manager.get_state(plugin_id)
    assert status.state == PluginLifecycleState.DEGRADED
    assert plugin_state_manager.can_accept_work(plugin_id)

    # ERROR state -> can_accept_work is False
    plugin_state_manager.set_state(
        plugin_id, PluginLifecycleState.ERROR, "Database connection lost"
    )
    status = plugin_state_manager.get_state(plugin_id)
    assert status.state == PluginLifecycleState.ERROR
    assert not plugin_state_manager.can_accept_work(plugin_id)


def test_binary_runner_process_registration():
    """Verify CoreBinaryRunner registers PID with supervisor during binary execution."""
    mock_process = MagicMock()
    mock_process.pid = 4321
    mock_process.stdout = ["output line"]
    mock_process.stderr = []
    mock_process.returncode = 0

    with patch("subprocess.Popen", return_value=mock_process):
        # During execution, supervisor should track the PID
        def check_supervisor_during_wait(timeout=None):
            active = supervisor.get_active_processes("core.binary_runner")
            assert len(active) == 1
            assert active[0].pid == 4321
            assert active[0].task_name == "echo"

        mock_process.wait.side_effect = check_supervisor_during_wait

        code, out, err = CoreBinaryRunner.run_binary(
            ["echo", "hello"], owner_id="core.binary_runner"
        )
        assert code == 0

    # After completion, process should be unregistered
    assert len(supervisor.get_active_processes("core.binary_runner")) == 0
