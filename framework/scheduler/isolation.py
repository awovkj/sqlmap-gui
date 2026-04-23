from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass
class IsolationResult:
    value: Any = None
    error: Optional[str] = None


def run_isolated(callback: Callable[..., Any], *args, **kwargs) -> IsolationResult:
    try:
        return IsolationResult(value=callback(*args, **kwargs))
    except Exception as exc:
        return IsolationResult(error=str(exc))
