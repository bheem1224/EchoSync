import inspect
import queue
import threading
import time
from typing import Any

from core.task_manager.models import OwnerType, ProcessCategory
from core.task_manager.supervisor import supervisor
from core.tiered_logger import get_logger

logger = get_logger("core.event_bus")

_SHUTDOWN_SENTINEL = object()


class EventBus:
    """Simple in-memory event bus for short-lived progress events.

    Stores events per channel with monotonic integer IDs so clients can poll
    incrementally without missing events.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: dict[str, list[dict[str, Any]]] = {}
        self._subscribers: dict[str, list] = {}
        self._queue = queue.Queue()
        self._dispatcher: threading.Thread | None = None
        self._reg_id: str | None = None
        self._running = False
        self.start()

    def start(self) -> None:
        """Start the background event dispatcher thread if not already running."""
        with self._lock:
            if self._running and self._dispatcher and self._dispatcher.is_alive():
                return
            self._running = True
            self._dispatcher, self._reg_id = supervisor.spawn_supervised_thread(
                target=self._dispatcher_loop,
                name="EventBusDispatcher",
                owner_id="core.event_bus",
                owner_type=OwnerType.CORE,
                category=ProcessCategory.CORE_SYSTEM,
                bound_to_general_pool=False,
            )

    def stop(self, timeout: float = 5.0) -> None:
        """Gracefully stop the event dispatcher thread, draining all queued events."""
        with self._lock:
            if not self._running:
                return
            self._running = False

        # Signal shutdown sentinel
        self._queue.put(_SHUTDOWN_SENTINEL)

        if self._dispatcher and self._dispatcher.is_alive():
            self._dispatcher.join(timeout=timeout)
            if self._dispatcher.is_alive():
                logger.warning(f"EventBus dispatcher thread did not terminate within {timeout}s")
            self._dispatcher = None
        if self._reg_id:
            supervisor.unregister_process(self._reg_id)
            self._reg_id = None

    def _dispatcher_loop(self):
        while True:
            try:
                item = self._queue.get()
                if item is _SHUTDOWN_SENTINEL:
                    self._queue.task_done()
                    # Drain any remaining events before exiting
                    while not self._queue.empty():
                        try:
                            remaining = self._queue.get_nowait()
                            if remaining is not _SHUTDOWN_SENTINEL:
                                self._dispatch_event(*remaining)
                            self._queue.task_done()
                        except queue.Empty:
                            break
                    break

                event_name, payload, serialized, specific, universal = item
                self._dispatch_event(event_name, payload, serialized, specific, universal)
                self._queue.task_done()
            except Exception as e:
                logger.error(f"Fatal error in event dispatcher loop: {e}", exc_info=True)

    def _dispatch_event(self, event_name, payload, serialized, specific, universal):
        for handler in specific:
            try:
                sig = inspect.signature(handler)
                if "_serialized" in sig.parameters or any(
                    p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
                ):
                    handler(payload, _serialized=serialized)
                else:
                    handler(payload)
            except Exception as e:
                logger.error(
                    f"Error in event handler for {event_name}: {e}",
                    exc_info=True,
                )

        for handler in universal:
            try:
                sig = inspect.signature(handler)
                if "_serialized" in sig.parameters or any(
                    p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
                ):
                    handler(payload, _serialized=serialized)
                else:
                    handler(payload)
            except Exception as e:
                logger.error(f"Error in universal event handler: {e}", exc_info=True)

    def subscribe(self, event_name_or_handler, handler=None):
        if handler is None:
            event_name = "*"
            h = event_name_or_handler
        else:
            event_name = event_name_or_handler
            h = handler

        with self._lock:
            if event_name not in self._subscribers:
                self._subscribers[event_name] = []
            self._subscribers[event_name].append(h)

    def unsubscribe(self, event_name_or_handler, handler=None):
        if handler is None:
            event_name = "*"
            h = event_name_or_handler
        else:
            event_name = event_name_or_handler
            h = handler

        with self._lock:
            if event_name in self._subscribers:
                try:
                    self._subscribers[event_name].remove(h)
                except ValueError:
                    pass

    def publish_lightweight(self, payload: dict):
        import inspect
        import zlib

        frame = inspect.currentframe()
        try:
            caller_module = inspect.getmodule(frame.f_back)
            caller_name = caller_module.__name__ if caller_module else "unknown"

            payload["_origin"] = caller_name
            if caller_name.startswith("core."):
                payload["_passport"] = 0
            else:
                payload["_passport"] = zlib.crc32(caller_name.encode())
        finally:
            del frame
        event_name = payload.get("event", "UNKNOWN")

        with self._lock:
            specific = list(self._subscribers.get(event_name, []))
            universal = list(self._subscribers.get("*", []))

        # --- Passport Enforcement ---
        import inspect
        import zlib

        caller_mod = inspect.currentframe().f_back.f_globals.get("__name__", "unknown")
        if caller_mod.startswith("core."):
            origin_passport = 0
            origin_name = "core"
        else:
            origin_name = caller_mod.split(".")[-1] if "." in caller_mod else caller_mod
            origin_passport = zlib.crc32(origin_name.encode("utf-8"))

        payload["_origin"] = origin_name
        payload["_passport"] = origin_passport
        # ----------------------------

        # OPTIMIZATION: Serialize JSON once for all network subscribers to prevent
        # duplicate CPU work during fan-out broadcasts.
        # Pass serialized string via kwargs to avoid payload mutation.
        import json

        try:
            serialized = json.dumps(payload, default=str)
        except Exception:
            serialized = "{}"

        # Push to background dispatcher queue to avoid blocking publisher thread
        import copy

        self._queue.put((event_name, copy.deepcopy(payload), serialized, specific, universal))

    def publish(self, *args, **kwargs):
        # Handle Phase-2 target API: publish(payload_dict)
        if len(args) == 1 and isinstance(args[0], dict):
            return self.publish_lightweight(args[0])

        # Handle Transitional API: publish(event_name, payload_dict)
        if len(args) == 2 and isinstance(args[0], str) and isinstance(args[1], dict):
            payload = args[1]
            if "event" not in payload:
                payload["event"] = args[0]
            return self.publish_lightweight(payload)

        # Handle Legacy API: publish(channel, event_type, data)
        if len(args) >= 2 and isinstance(args[0], str) and isinstance(args[1], str):
            channel = args[0]
            event_type = args[1]
            data = args[2] if len(args) > 2 else kwargs.get("data", {})

            # Send to lightweight subscribers too just in case
            self.publish_lightweight({"event": event_type, "channel": channel, "data": data})

            # Legacy logic
            payload = data or {}
            with self._lock:
                bucket = self._events.setdefault(channel, [])
                event_id = len(bucket)
                envelope: dict[str, Any] = {
                    "id": event_id,
                    "ts": time.time(),
                    "type": event_type,
                    "data": payload,
                }
                bucket.append(envelope)
                return envelope

        # Fallback if someone uses kwargs?
        if "channel" in kwargs and "event_type" in kwargs:
            return self.publish(kwargs["channel"], kwargs["event_type"], kwargs.get("data", {}))

    def get_events(self, channel: str, since_id: int | None = None) -> list[dict[str, Any]]:
        """Return events for a channel optionally after a given event id."""
        with self._lock:
            bucket = self._events.get(channel, [])
            if since_id is None:
                return list(bucket)
            return [evt for evt in bucket if evt["id"] > since_id]

    def clear(self, channel: str) -> None:
        """Clear events for a channel (used after sync completes)."""
        with self._lock:
            if channel in self._events:
                del self._events[channel]


event_bus = EventBus()
