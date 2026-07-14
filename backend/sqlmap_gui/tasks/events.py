from __future__ import annotations

import threading
from collections import deque
from typing import Any


class EventHub:
    """In-memory pub/sub buffer for task events consumed by the SSE stream.

    Events are retained in a bounded ring buffer so a long-lived session cannot
    grow memory without limit. Live SSE clients poll ``snapshot`` roughly once a
    second and never fall far enough behind to notice the cap; historical logs
    are always available from the database via the task-logs endpoint.
    """

    def __init__(self, max_events: int = 5000) -> None:
        self._events: deque[dict[str, Any]] = deque(maxlen=max_events)
        self._lock = threading.Lock()
        self._next_id = 1

    def publish(self, event_type: str, task_id: str | None, message: str, level: str = "info", **extra: Any) -> dict[str, Any]:
        with self._lock:
            event = {
                "id": self._next_id,
                "type": event_type,
                "task_id": task_id,
                "level": level,
                "message": message,
                **extra,
            }
            self._next_id += 1
            self._events.append(event)
            return dict(event)

    def snapshot(self, after_id: int = 0) -> list[dict[str, Any]]:
        with self._lock:
            # Events are appended in ascending id order, so once we pass the
            # cursor everything after it is newer; stop scanning early otherwise.
            if not self._events or int(self._events[-1]["id"]) <= after_id:
                return []
            return [dict(event) for event in self._events if int(event["id"]) > after_id]
