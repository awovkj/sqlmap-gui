from __future__ import annotations

from framework.model.finding import RiskFinding
from framework.model.request import TargetRequest
from framework.model.request import TestPoint


class Plugin:
    def before_target(self, target: TargetRequest) -> None:
        return None

    def after_target(self, target: TargetRequest) -> None:
        return None

    def before_request(self, target: TargetRequest, test_point: TestPoint | None = None) -> None:
        return None

    def after_finding(self, finding: RiskFinding) -> None:
        return None
