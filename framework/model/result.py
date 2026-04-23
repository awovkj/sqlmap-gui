from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from framework.model.finding import RiskFinding


@dataclass
class AssessmentStats:
    targets: int = 0
    test_points: int = 0
    findings: int = 0
    high_risk: int = 0
    medium_risk: int = 0
    low_risk: int = 0
    errors: int = 0


@dataclass
class AssessmentResult:
    started_at: str
    finished_at: str
    stats: AssessmentStats = field(default_factory=AssessmentStats)
    findings: List[RiskFinding] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)
