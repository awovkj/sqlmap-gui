from __future__ import annotations

from framework.model.result import AssessmentResult


def build_summary(result: AssessmentResult) -> str:
    stats = result.stats
    return (
        f"targets={stats.targets} test_points={stats.test_points} findings={stats.findings} "
        f"high={stats.high_risk} medium={stats.medium_risk} low={stats.low_risk} errors={stats.errors}"
    )
