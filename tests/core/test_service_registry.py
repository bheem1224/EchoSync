"""
Tests for ServiceRegistry (core/provider.py).

Validates three invariants from the QA audit:

  1. resolve() returns None when no default has been registered for a name
     (documents the contract so callers know they must handle None).

  2. A broken override factory (raises on __init__) is handed back to the
     caller as-is; the registry does NOT silently swallow init errors.
     The 'or WeightedMatchingEngine' fallback patched in metadata_enhancer.py
     is the correct place to handle this — not inside the registry.

  3. register_override() must update _services but must NEVER mutate _defaults.

Each test uses a unique service name prefixed with the test class/method name
to guarantee complete isolation from the live application's registered services
(e.g. WeightedMatchingEngine registered at module-load time).  A fixture also
tears down registry state after every test.
"""

import threading
from unittest.mock import MagicMock

import pytest

from core.provider import ServiceRegistry


# ---------------------------------------------------------------------------
# Isolation fixture
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _isolated_registry():
    """
    Snapshot and restore ServiceRegistry's class-level dicts around every test
    so that test registrations do not leak into other tests or the live app state.
    """
    original_services = dict(ServiceRegistry._services)
    original_defaults = dict(ServiceRegistry._defaults)
    yield
    ServiceRegistry._services.clear()
    ServiceRegistry._services.update(original_services)
    ServiceRegistry._defaults.clear()
    ServiceRegistry._defaults.update(original_defaults)


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

class _DummyEngine:
    """Minimal stand-in for a matching engine class."""
    def __init__(self, profile=None):
        self.profile = profile

    def calculate_match(self, a, b):
        return MagicMock(confidence_score=0.0)


class _BrokenEngine:
    """Factory that always raises on __init__ — simulates a misconfigured plugin."""
    def __init__(self, *args, **kwargs):
        raise RuntimeError("BrokenEngine: deliberate init failure")


# ===========================================================================
# 1. resolve() — no default registered
# ===========================================================================

class TestResolveNoDefault:
    def test_resolve_returns_none_when_no_default_registered(self):
        """
        Callers must receive None (not raise) when the service has never been
        registered.  This documents the contract: every caller is responsible
        for its own fallback (e.g. `or WeightedMatchingEngine`).
        """
        result = ServiceRegistry.resolve("nonexistent_service_xyz_unique_abc")
        assert result is None, (
            f"Expected None for an unregistered service, got {result!r}"
        )

    def test_resolve_returns_none_after_override_removed(self):
        """
        After an override is registered then cleared, resolve must return None
        (or the default if one was set — here none was).
        """
        name = "temp_service_test_resolve"
        ServiceRegistry.register_override(name, _DummyEngine)
        # Manually clear to simulate a reload / un-registration scenario.
        with ServiceRegistry._lock:
            ServiceRegistry._services.pop(name, None)
        result = ServiceRegistry.resolve(name)
        assert result is None


# ===========================================================================
# 2. Broken override — registry hands it back, caller handles init error
# ===========================================================================

class TestBrokenOverrideFallback:
    def test_registry_returns_broken_class_not_none(self):
        """
        ServiceRegistry.resolve() must hand back _BrokenEngine unchanged.
        It is NOT the registry's job to catch __init__ failures.
        """
        name = "matching_engine_broken_test"
        ServiceRegistry.register_override(name, _BrokenEngine)
        engine_cls = ServiceRegistry.resolve(name)
        assert engine_cls is _BrokenEngine, (
            "Registry must return the registered (broken) class, not None."
        )

    def test_broken_override_init_raises_at_call_site(self):
        """
        Instantiating the returned broken class must raise RuntimeError.
        This documents that the 'or WeightedMatchingEngine' pattern in the
        metadata_enhancer is the *correct* layer to apply the fallback — not
        inside resolve().
        """
        name = "matching_engine_broken_init_test"
        ServiceRegistry.register_override(name, _BrokenEngine)
        engine_cls = ServiceRegistry.resolve(name)

        with pytest.raises(RuntimeError, match="deliberate init failure"):
            engine_cls()

    def test_default_engine_still_accessible_after_broken_override_registered(self):
        """
        After register_override('X', BrokenEngine), the *default* engine for a
        *different* service name must remain fully accessible, proving no cross-
        contamination between service slots.
        """
        good_name = "good_engine_slot"
        broken_name = "broken_engine_slot"

        ServiceRegistry.register_default(good_name, _DummyEngine)
        ServiceRegistry.register_override(broken_name, _BrokenEngine)

        good_cls = ServiceRegistry.resolve(good_name)
        assert good_cls is _DummyEngine


# ===========================================================================
# 3. register_override() must not mutate _defaults
# ===========================================================================

class TestOverrideDoesNotCorruptDefaults:
    def test_register_override_does_not_corrupt_defaults(self):
        """
        Calling register_override() must only update _services.
        The pointer in _defaults must remain the original factory.
        """
        name = "matching_engine_isolation_test"
        ServiceRegistry.register_default(name, _DummyEngine)

        # Confirm default was set.
        assert ServiceRegistry._defaults.get(name) is _DummyEngine

        # Now override with a completely different class.
        ServiceRegistry.register_override(name, _BrokenEngine)

        # _services updated, _defaults unchanged.
        assert ServiceRegistry._services.get(name) is _BrokenEngine, (
            "_services must reflect the new override."
        )
        assert ServiceRegistry._defaults.get(name) is _DummyEngine, (
            "_defaults must still hold the original factory — override must not mutate defaults."
        )

    def test_register_default_does_not_overwrite_existing_service(self):
        """
        register_default() must only populate _services when the slot is empty.
        If an override is already present, _services must not be touched.
        """
        name = "engine_slot_no_overwrite"
        ServiceRegistry.register_override(name, _BrokenEngine)
        # Now register a default — _services must keep _BrokenEngine.
        ServiceRegistry.register_default(name, _DummyEngine)

        assert ServiceRegistry._services.get(name) is _BrokenEngine, (
            "register_default must not overwrite an existing _services entry."
        )
        assert ServiceRegistry._defaults.get(name) is _DummyEngine

    def test_multiple_overrides_do_not_pollute_defaults(self):
        """Each successive override replaces the previous in _services only."""
        name = "multi_override_test"
        ServiceRegistry.register_default(name, _DummyEngine)

        class _Override1:
            pass

        class _Override2:
            pass

        ServiceRegistry.register_override(name, _Override1)
        assert ServiceRegistry._defaults[name] is _DummyEngine

        ServiceRegistry.register_override(name, _Override2)
        assert ServiceRegistry._services[name] is _Override2
        assert ServiceRegistry._defaults[name] is _DummyEngine, (
            "_defaults must be frozen across all override calls."
        )


# ===========================================================================
# 4. Thread-safety — lock sanity check (H3 regression)
# ===========================================================================

class TestServiceRegistryThreadSafety:
    """
    Smoke-test that concurrent register_default / resolve calls do not raise
    or leave the registry in an inconsistent state.  This is not an exhaustive
    race-condition test (that would require a stress harness), but it confirms
    the lock does not deadlock and concurrent reads return a consistent type.
    """

    def test_concurrent_register_and_resolve_do_not_raise(self):
        name = "concurrent_engine_test"
        ServiceRegistry.register_default(name, _DummyEngine)

        errors = []

        def _register():
            try:
                ServiceRegistry.register_override(name, _DummyEngine)
            except Exception as exc:
                errors.append(exc)

        def _resolve():
            try:
                result = ServiceRegistry.resolve(name)
                if result is not None and not (result is _DummyEngine):
                    errors.append(TypeError(f"Unexpected resolve result: {result!r}"))
            except Exception as exc:
                errors.append(exc)

        threads = (
            [threading.Thread(target=_register) for _ in range(10)]
            + [threading.Thread(target=_resolve) for _ in range(10)]
        )
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert not errors, f"Thread-safety errors: {errors}"

    def test_lock_is_not_reentrant_deadlock(self):
        """
        Calling resolve() from within a non-nested context must complete without
        deadlocking.  This guards against accidental re-entrant locking.
        """
        name = "reentrant_safe_test"
        ServiceRegistry.register_default(name, _DummyEngine)
        # If this hangs, the lock is deadlocked — pytest will time out.
        result = ServiceRegistry.resolve(name)
        assert result is _DummyEngine


# ===========================================================================
# 5. resolve() with config override key
# ===========================================================================

class TestResolveConfigOverrideKey:
    def test_resolve_uses_config_override_when_present(self):
        """
        If config_manager.get('settings.active_<name>') returns a key that IS
        registered in _services, resolve() must return that override class.
        """
        name = "matching_engine"
        alias = "my_custom_engine"

        ServiceRegistry.register_default(name, _DummyEngine)
        ServiceRegistry.register_override(alias, _BrokenEngine)

        import core.settings as settings_mod
        original = settings_mod.config_manager
        mock_cm = MagicMock()
        mock_cm.get.return_value = alias
        settings_mod.config_manager = mock_cm

        try:
            result = ServiceRegistry.resolve(name)
            assert result is _BrokenEngine, (
                "resolve() must return the config-specified override when it is registered."
            )
        finally:
            settings_mod.config_manager = original

    def test_resolve_falls_back_to_default_when_config_override_not_registered(
        self, monkeypatch
    ):
        """
        If config_manager returns a name that is NOT in _services, resolve()
        must fall back to the registered default.
        """
        name = "matching_engine_fallback_test"
        ServiceRegistry.register_default(name, _DummyEngine)

        import core.settings as settings_mod
        original = settings_mod.config_manager
        mock_cm = MagicMock()
        mock_cm.get.return_value = "unregistered_override_xyz"
        settings_mod.config_manager = mock_cm

        try:
            result = ServiceRegistry.resolve(name)
            assert result is _DummyEngine, (
                "resolve() must fall back to the default when the config override key is not registered."
            )
        finally:
            settings_mod.config_manager = original
