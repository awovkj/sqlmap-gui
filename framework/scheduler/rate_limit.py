from __future__ import annotations

import threading
import time
from contextlib import contextmanager


class HostRequestController:
    def __init__(self, requests_per_second: float, per_host: int):
        self.interval = 0.0 if requests_per_second <= 0 else 1.0 / requests_per_second
        self.per_host = max(1, per_host)
        self._timestamps: dict[str, float] = {}
        self._timestamp_lock = threading.Lock()
        self._semaphores: dict[str, threading.Semaphore] = {}
        self._semaphore_lock = threading.Lock()

    def _get_semaphore(self, host: str) -> threading.Semaphore:
        with self._semaphore_lock:
            semaphore = self._semaphores.get(host)
            if semaphore is None:
                semaphore = threading.Semaphore(self.per_host)
                self._semaphores[host] = semaphore
            return semaphore

    @contextmanager
    def gate(self, host: str):
        semaphore = self._get_semaphore(host)
        semaphore.acquire()
        try:
            wait_for = 0.0
            if self.interval > 0:
                with self._timestamp_lock:
                    now = time.monotonic()
                    ready_at = max(now, self._timestamps.get(host, now))
                    wait_for = max(0.0, ready_at - now)
                    self._timestamps[host] = ready_at + self.interval
            if wait_for > 0:
                time.sleep(wait_for)
            yield
        finally:
            semaphore.release()
