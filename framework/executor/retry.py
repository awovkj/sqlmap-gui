from __future__ import annotations

import time
from typing import Callable, Tuple, Type


def run_with_retry(
    func: Callable[[], object],
    attempts: int,
    backoff_seconds: float,
    retryable_exceptions: Tuple[Type[BaseException], ...],
):
    last_error = None
    for attempt in range(1, max(1, attempts) + 1):
        try:
            return func()
        except retryable_exceptions as exc:  # type: ignore[arg-type]
            last_error = exc
            if attempt >= attempts:
                break
            if backoff_seconds > 0:
                time.sleep(backoff_seconds * attempt)
    if last_error is not None:
        raise last_error
    return func()
