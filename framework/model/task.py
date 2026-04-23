from __future__ import annotations

from dataclasses import dataclass

from framework.model.request import TargetRequest
from framework.model.request import TestPoint


@dataclass
class AssessmentTask:
    target: TargetRequest
    test_point: TestPoint
    probe_value: str
