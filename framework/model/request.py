from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class TargetRequest:
    method: str
    url: str
    headers: Dict[str, str] = field(default_factory=dict)
    body: str = ""
    source: str = "direct"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestPoint:
    name: str
    location: str
    value: Any
    path: str
    content_type: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
