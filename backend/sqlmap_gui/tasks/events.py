from __future__ import annotations

import threading
from typing import Any


class EventHub:
    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []
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
            return [dict(event) for event in self._events if int(event["id"]) > after_id]
