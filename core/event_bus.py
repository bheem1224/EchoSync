import threading
import time
from typing import Any, Dict, List, Optional


class EventBus:
    """Simple in-memory event bus for short-lived progress events.

    Stores events per channel with monotonic integer IDs so clients can poll
    incrementally without missing events.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: Dict[str, List[Dict[str, Any]]] = {}
        self._subscribers: Dict[str, List] = {}


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
        event_name = payload.get("event", "UNKNOWN")

        with self._lock:
            specific = list(self._subscribers.get(event_name, []))
            universal = list(self._subscribers.get("*", []))

        # OPTIMIZATION: Serialize JSON once for all network subscribers to prevent
        # duplicate CPU work during fan-out broadcasts.
        # Pass serialized string via kwargs to avoid payload mutation.
        import json
        try:
            serialized = json.dumps(payload, default=str)
        except Exception:
            serialized = "{}"

        for handler in specific:
            try:
                # Check if handler accepts kwargs, otherwise just send payload
                import inspect
                sig = inspect.signature(handler)
                if '_serialized' in sig.parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
                    handler(payload, _serialized=serialized)
                else:
                    handler(payload)
            except Exception as e:
                import logging
                logging.getLogger("event_bus").error(f"Error in event handler for {event_name}: {e}", exc_info=True)

        for handler in universal:
            try:
                import inspect
                sig = inspect.signature(handler)
                if '_serialized' in sig.parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
                    handler(payload, _serialized=serialized)
                else:
                    handler(payload)
            except Exception as e:
                import logging
                logging.getLogger("event_bus").error(f"Error in universal event handler: {e}", exc_info=True)

    def publish(self, *args, **kwargs):
        # Handle Phase-2 target API: publish(payload_dict)
        if len(args) == 1 and isinstance(args[0], dict):
            return self.publish_lightweight(args[0])

        # Handle Transitional API: publish(event_name, payload_dict)
        if len(args) == 2 and isinstance(args[0], str) and isinstance(args[1], dict):
            return self.publish_lightweight(args[1])

        # Handle Legacy API: publish(channel, event_type, data)
        if len(args) >= 2 and isinstance(args[0], str) and isinstance(args[1], str):
            channel = args[0]
            event_type = args[1]
            data = args[2] if len(args) > 2 else kwargs.get("data", {})

            # Send to lightweight subscribers too just in case
            self.publish_lightweight({
                "event": event_type,
                "channel": channel,
                "data": data
            })

            # Legacy logic
            payload = data or {}
            with self._lock:
                bucket = self._events.setdefault(channel, [])
                event_id = len(bucket)
                envelope: Dict[str, Any] = {
                    "id": event_id,
                    "ts": time.time(),
                    "type": event_type,
                    "data": payload,
                }
                bucket.append(envelope)
                return envelope

        # Fallback if someone uses kwargs?
        if 'channel' in kwargs and 'event_type' in kwargs:
            return self.publish(kwargs['channel'], kwargs['event_type'], kwargs.get('data', {}))


    def get_events(self, channel: str, since_id: Optional[int] = None) -> List[Dict[str, Any]]:
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
