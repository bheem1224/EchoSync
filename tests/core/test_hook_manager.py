"""
Tests for HookManager (core/hook_manager.py).

Key invariants verified:
    1. Synchronous hooks chain correctly and return the final transformed value.
    2. An async hook NEVER poisons the return value — the original pre-hook value
       is restored, the coroutine is closed (no ResourceWarning), and the chain
       continues with the next registered hook.
    3. A crashing sync hook also restores the pre-hook value and continues the chain.
    4. A hook-name with no registered filters returns the default value unchanged.
"""

import asyncio
import types

import pytest

from core.hook_manager import HookManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def hm():
    """Return a fresh, isolated HookManager for each test (not the global singleton)."""
    return HookManager()


# ===========================================================================
# Basic synchronous behaviour
# ===========================================================================

class TestSyncFilters:
    def test_no_filters_returns_default_value(self, hm):
        result = hm.apply_filters("unregistered_hook", "original")
        assert result == "original"

    def test_single_sync_hook_transforms_value(self, hm):
        hm.add_filter("greet", lambda v: v + " world")
        assert hm.apply_filters("greet", "hello") == "hello world"

    def test_chained_sync_hooks_apply_in_registration_order(self, hm):
        hm.add_filter("pipe", lambda v: v + "_A")
        hm.add_filter("pipe", lambda v: v + "_B")
        hm.add_filter("pipe", lambda v: v + "_C")
        assert hm.apply_filters("pipe", "start") == "start_A_B_C"

    def test_sync_hook_receives_extra_args(self, hm):
        hm.add_filter("concat", lambda v, suffix: v + suffix)
        result = hm.apply_filters("concat", "base", "_extra")
        assert result == "base_extra"

    def test_sync_hook_receives_kwargs(self, hm):
        hm.add_filter("concat", lambda v, suffix="": v + suffix)
        result = hm.apply_filters("concat", "base", suffix="_kw")
        assert result == "base_kw"


# ===========================================================================
# H1 — Async hook poisoning (the core regression test)
# ===========================================================================

class TestAsyncHookGuard:
    """
    Validates the fix from audit finding H1:
    'The Async Guard Is Broken — the coroutine survives and poisons the return value.'

    After the patch, the coroutine must be:
      - detected via asyncio.iscoroutine()
      - closed immediately (prevents ResourceWarning)
      - NOT used as the new value for subsequent hooks
    """

    def test_async_hook_does_not_poison_return_value(self, hm):
        """
        Registering an async hook must not corrupt the return value.
        The returned value must remain the original default, not a coroutine.
        """
        async def bad_hook(val):
            return val + "_async_result"

        hm.add_filter("test_hook", bad_hook)
        result = hm.apply_filters("test_hook", "original")

        assert result == "original", (
            f"Expected 'original' but got {type(result)}: {result!r}. "
            "The async hook must not replace the value."
        )

    def test_async_hook_return_is_not_a_coroutine(self, hm):
        """The final returned value must never be a coroutine object."""
        async def bad_hook(val):
            return "async_corrupted"

        hm.add_filter("check_type", bad_hook)
        result = hm.apply_filters("check_type", "safe")

        assert not asyncio.iscoroutine(result), (
            "apply_filters must never return a live coroutine object. "
            "It would be silently lost and generate a ResourceWarning."
        )

    def test_async_hook_coroutine_is_closed_no_resource_warning(
        self, hm, recwarn
    ):
        """
        The coroutine returned by the async hook must be .close()d by the
        HookManager so Python does not emit a 'coroutine was never awaited'
        ResourceWarning.
        """
        executed_coroutines = []

        async def bad_hook(val):
            return val

        # Wrap so we can capture the coroutine object before HookManager sees it.
        original_bad_hook = bad_hook

        async def spy_hook(val):
            coro = original_bad_hook(val)
            executed_coroutines.append(coro)
            # Return the coroutine directly to simulate the plugin returning it.
            # We immediately close our reference so that only HookManager's
            # reference (inside apply_filters) can trigger the ResourceWarning.
            return coro

        hm.add_filter("coro_close", spy_hook)
        hm.apply_filters("coro_close", "value")

        # Close our spy reference to avoid a warning from the test itself.
        for c in executed_coroutines:
            if not c.cr_frame:  # already closed
                pass
            else:
                c.close()

        # Assert no ResourceWarning was emitted during apply_filters.
        resource_warnings = [
            w for w in recwarn.list if issubclass(w.category, ResourceWarning)
        ]
        assert not resource_warnings, (
            f"ResourceWarning raised by unclosed coroutine: {resource_warnings}"
        )

    def test_chained_hooks_skip_async_and_continue(self, hm):
        """
        Register [bad async hook, good sync hook].
        The good sync hook must still fire and must receive the original
        (un-poisoned) value, not the async result.
        """
        async def bad_hook(val):
            return "ASYNC_POISON"

        def good_hook(val):
            return val + "_good"

        hm.add_filter("chain", bad_hook)
        hm.add_filter("chain", good_hook)
        result = hm.apply_filters("chain", "start")

        assert result == "start_good", (
            f"Expected 'start_good' but got {result!r}. "
            "The sync hook after the async hook must operate on the safe value."
        )

    def test_async_hook_between_two_sync_hooks(self, hm):
        """
        [sync hook A, async hook, sync hook B] — both sync hooks must execute
        on consecutive safe values; the async hook must be a transparent no-op.
        """
        hm.add_filter("triple", lambda v: v + "_A")

        async def middle_bad(val):
            return "POISON"

        hm.add_filter("triple", middle_bad)
        hm.add_filter("triple", lambda v: v + "_B")

        result = hm.apply_filters("triple", "start")
        assert result == "start_A_B", (
            f"Expected 'start_A_B' but got {result!r}. "
            "Async hook in the middle must be skipped cleanly."
        )

    def test_multiple_async_hooks_all_skipped(self, hm):
        """All async hooks in a chain must be skipped; the default is returned intact."""
        async def a1(v): return v + "_a1"
        async def a2(v): return v + "_a2"

        hm.add_filter("all_async", a1)
        hm.add_filter("all_async", a2)

        result = hm.apply_filters("all_async", "safe")
        assert result == "safe"


# ===========================================================================
# Crashing sync hook resilience
# ===========================================================================

class TestCrashingHookResilience:
    """A sync hook that raises must not corrupt the chain."""

    def test_crashing_hook_does_not_propagate_exception(self, hm):
        def exploding(val):
            raise RuntimeError("boom")

        hm.add_filter("boom_hook", exploding)
        # Must not raise.
        result = hm.apply_filters("boom_hook", "safe")
        assert result == "safe"

    def test_crashing_hook_between_good_hooks_chain_continues(self, hm):
        hm.add_filter("mixed", lambda v: v + "_before")

        def crasher(val):
            raise ValueError("mid-crash")

        hm.add_filter("mixed", crasher)
        hm.add_filter("mixed", lambda v: v + "_after")

        result = hm.apply_filters("mixed", "start")
        assert result == "start_before_after", (
            "Good hooks on either side of a crashing hook must both execute."
        )


# ===========================================================================
# add_filter
# ===========================================================================

class TestAddFilter:
    def test_add_filter_creates_new_hook_list(self, hm):
        assert "new_hook" not in hm._filters
        hm.add_filter("new_hook", lambda v: v)
        assert "new_hook" in hm._filters

    def test_add_filter_appends_to_existing_list(self, hm):
        cb_a = lambda v: v
        cb_b = lambda v: v
        hm.add_filter("append_test", cb_a)
        hm.add_filter("append_test", cb_b)
        assert hm._filters["append_test"] == [cb_a, cb_b]

    def test_different_hooks_are_isolated(self, hm):
        hm.add_filter("hook_x", lambda v: v + "_x")
        hm.add_filter("hook_y", lambda v: v + "_y")
        assert hm.apply_filters("hook_x", "val") == "val_x"
        assert hm.apply_filters("hook_y", "val") == "val_y"
