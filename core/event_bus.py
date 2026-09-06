import threading
import time
from typing import Any


class EventBus:
    """Simple in-memory event bus for short-lived progress events.

    Stores events per channel with monotonic integer IDs so clients can poll
    incrementally without missing events.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: dict[str, list[dict[str, Any]]] = {}
        self._subscribers: dict[str, list] = {}
        import queue

        self._queue = queue.Queue()
        self._dispatcher = threading.Thread(target=self._dispatcher_loop, daemon=True)
        self._dispatcher.start()

    def _dispatcher_loop(self):
        import inspect
        import logging

        while True:
            try:
                event_name, payload, serialized, specific, universal = self._queue.get()

                for handler in specific:
                    try:
                        sig = inspect.signature(handler)
                        if "_serialized" in sig.parameters or any(
                            p.kind == inspect.Parameter.VAR_KEYWORD
                            for p in sig.parameters.values()
                        ):
                            handler(payload, _serialized=serialized)
                        else:
                            handler(payload)
                    except Exception as e:
                        logging.getLogger("event_bus").error(
                            f"Error in event handler for {event_name}: {e}",
                            exc_info=True,
                        )

                for handler in universal:
                    try:
                        sig = inspect.signature(handler)
                        if "_serialized" in sig.parameters or any(
                            p.kind == inspect.Parameter.VAR_KEYWORD
                            for p in sig.parameters.values()
                        ):
                            handler(payload, _serialized=serialized)
                        else:
                            handler(payload)
                    except Exception as e:
                        logging.getLogger("event_bus").error(
                            f"Error in universal event handler: {e}", exc_info=True
                        )

            except Exception as e:
                logging.getLogger("event_bus").error(
                    f"Fatal error in event dispatcher loop: {e}", exc_info=True
                )

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

        self._queue.put(
            (event_name, copy.deepcopy(payload), serialized, specific, universal)
        )

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
            self.publish_lightweight(
                {"event": event_type, "channel": channel, "data": data}
            )

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
            return self.publish(
                kwargs["channel"], kwargs["event_type"], kwargs.get("data", {})
            )

    def get_events(
        self, channel: str, since_id: int | None = None
    ) -> list[dict[str, Any]]:
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
