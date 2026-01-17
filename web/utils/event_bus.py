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

    def publish(self, channel: str, event_type: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Publish an event and return the stored envelope."""
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
