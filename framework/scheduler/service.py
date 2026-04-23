from __future__ import annotations

import datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

from framework.analyzer.diff_engine import compare_responses
from framework.analyzer.scorer import build_finding
from framework.config.schema import FrameworkConfig
from framework.executor.client import RequestExecutor
from framework.model.result import AssessmentResult
from framework.model.result import AssessmentStats
from framework.model.task import AssessmentTask
from framework.plugins.manager import PluginManager
from framework.scheduler.isolation import run_isolated


PROBE_SUFFIXES = ["'", '"', " or 1=1", "--probe--"]


class AssessmentScheduler:
    def __init__(self, config: FrameworkConfig, plugin_manager: PluginManager | None = None):
        self.config = config
        self.plugin_manager = plugin_manager or PluginManager([])
        self.executor = RequestExecutor(config)

    def close(self) -> None:
        self.executor.close()

    def _build_probe(self, base_value: object, index: int) -> str:
        suffix = PROBE_SUFFIXES[index % len(PROBE_SUFFIXES)]
        return f"{base_value}{suffix}"

    def _calculate_stability(self, responses) -> float:
        if not responses:
            return 0.0
        first = responses[0]
        first_signature = (first.status_code, len(first.body or ""), first.error or "")
        matches = 0
        for response in responses:
            signature = (response.status_code, len(response.body or ""), response.error or "")
            if signature == first_signature:
                matches += 1
        return matches / float(len(responses))

    def _execute_task(self, task: AssessmentTask):
        self.plugin_manager.emit("before_request", task.target, task.test_point)
        baseline = self.executor.execute(task.target, label=f"baseline:{task.test_point.path}")
        candidate_target = self.executor.build_probe_request(task.target, task.test_point, task.probe_value)
        candidate_responses = []
        for repeat_index in range(self.config.analyzer.repeat_count):
            candidate_responses.append(
                self.executor.execute(
                    candidate_target,
                    label=f"probe:{task.test_point.path}:{task.probe_value}:{repeat_index}",
                )
            )
        candidate = candidate_responses[0]
        difference = compare_responses(baseline, candidate, self.config.analyzer)
        stability = self._calculate_stability(candidate_responses)
        finding = build_finding(task.target, task.test_point, baseline, candidate, difference, self.config.analyzer, stability)
        self.plugin_manager.emit("after_finding", finding)
        return finding

    def run(self, targets, test_points_by_target) -> AssessmentResult:
        started_at = dt.datetime.utcnow().isoformat() + "Z"
        result = AssessmentResult(started_at=started_at, finished_at=started_at)
        result.stats.targets = len(targets)
        tasks: List[AssessmentTask] = []

        for target in targets:
            self.plugin_manager.emit("before_target", target)
            for index, point in enumerate(test_points_by_target.get(target.url, [])):
                result.stats.test_points += 1
                tasks.append(AssessmentTask(target=target, test_point=point, probe_value=self._build_probe(point.value, index)))

        with ThreadPoolExecutor(max_workers=self.config.concurrency.workers) as executor:
            futures = [executor.submit(run_isolated, self._execute_task, task) for task in tasks]
            for future in as_completed(futures):
                isolated = future.result()
                if isolated.error:
                    result.errors.append(isolated.error)
                    result.stats.errors += 1
                    continue
                finding = isolated.value
                if finding.score <= 0:
                    continue
                result.findings.append(finding)
                result.stats.findings += 1
                if finding.risk_level == "high":
                    result.stats.high_risk += 1
                elif finding.risk_level == "medium":
                    result.stats.medium_risk += 1
                elif finding.risk_level == "low":
                    result.stats.low_risk += 1

        for target in targets:
            self.plugin_manager.emit("after_target", target)
        result.finished_at = dt.datetime.utcnow().isoformat() + "Z"
        return result
