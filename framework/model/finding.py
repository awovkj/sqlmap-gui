from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ResponseSnapshot:
    status_code: Optional[int]
    headers: Dict[str, str] = field(default_factory=dict)
    body: str = ""
    elapsed_ms: int = 0
    error: Optional[str] = None


@dataclass
class ResponseDifference:
    status_changed: bool
    length_delta: int
    similarity: float
    added_keywords: List[str] = field(default_factory=list)
    removed_keywords: List[str] = field(default_factory=list)
    baseline_length: int = 0
    candidate_length: int = 0
    error_changed: bool = False


@dataclass
class RiskFinding:
    target_url: str
    method: str
    test_point_name: str
    test_point_location: str
    risk_level: str
    confidence: str
    score: int
    stability: float
    recommendation: str
    evidence: List[str] = field(default_factory=list)
    baseline: ResponseSnapshot = field(default_factory=lambda: ResponseSnapshot(status_code=None))
    candidate: ResponseSnapshot = field(default_factory=lambda: ResponseSnapshot(status_code=None))
    difference: ResponseDifference = field(
        default_factory=lambda: ResponseDifference(status_changed=False, length_delta=0, similarity=1.0)
    )
