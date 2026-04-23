from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Any, Optional


class ResponseCache:
    def __init__(self, enabled: bool = True, ttl_seconds: int = 300, max_entries: int = 512):
        self.enabled = enabled
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._lock = threading.Lock()
        self._entries: OrderedDict[str, tuple[float, Any]] = OrderedDict()

    def get(self, key: str) -> Optional[Any]:
        if not self.enabled:
            return None
        now = time.time()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if expires_at < now:
                self._entries.pop(key, None)
                return None
            self._entries.move_to_end(key)
            return value

    def set(self, key: str, value: Any) -> None:
        if not self.enabled:
            return
        expires_at = time.time() + self.ttl_seconds
        with self._lock:
            self._entries[key] = (expires_at, value)
            self._entries.move_to_end(key)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)
