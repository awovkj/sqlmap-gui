from __future__ import annotations

from framework.config.schema import AnalyzerConfig
from framework.model.finding import ResponseDifference
from framework.model.finding import ResponseSnapshot
from framework.model.finding import RiskFinding
from framework.model.request import TargetRequest
from framework.model.request import TestPoint


def _risk_from_score(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    if score >= 15:
        return "low"
    return "informational"


def _confidence_from_stability(stability: float) -> str:
    if stability >= 0.9:
        return "high"
    if stability >= 0.6:
        return "medium"
    return "low"


def build_finding(
    target: TargetRequest,
    test_point: TestPoint,
    baseline: ResponseSnapshot,
    candidate: ResponseSnapshot,
    difference: ResponseDifference,
    config: AnalyzerConfig,
    stability: float,
) -> RiskFinding:
    score = 0
    evidence = []

    if difference.status_changed:
        baseline_status = baseline.status_code or 0
        candidate_status = candidate.status_code or 0
        if baseline_status // 100 != candidate_status // 100:
            score += 35
        else:
            score += 25
        evidence.append(f"状态码从 {baseline.status_code} 变为 {candidate.status_code}")

    if difference.length_delta >= config.length_delta_threshold * 3:
        score += 25
        evidence.append(f"响应长度显著变化 {difference.length_delta} 字节")
    elif difference.length_delta >= config.length_delta_threshold:
        score += 15
        evidence.append(f"响应长度变化 {difference.length_delta} 字节")

    similarity_gap = config.similarity_threshold - difference.similarity
    if similarity_gap >= 0.25:
        score += 25
        evidence.append(f"响应相似度大幅降至 {difference.similarity:.3f}")
    elif difference.similarity < config.similarity_threshold:
        score += 15
        evidence.append(f"响应相似度降至 {difference.similarity:.3f}")

    if difference.added_keywords:
        score += min(20, 5 * len(difference.added_keywords))
        evidence.append("新增关键字: " + ", ".join(difference.added_keywords))
    if difference.removed_keywords:
        score += min(10, 3 * len(difference.removed_keywords))
        evidence.append("消失关键字: " + ", ".join(difference.removed_keywords))
    if difference.error_changed:
        score += 12
        evidence.append("错误状态发生变化")

    elapsed_delta = abs((candidate.elapsed_ms or 0) - (baseline.elapsed_ms or 0))
    if elapsed_delta >= 1500:
        score += 12
        evidence.append(f"响应时间变化 {elapsed_delta}ms")
    elif elapsed_delta >= 500:
        score += 6
        evidence.append(f"响应时间变化 {elapsed_delta}ms")

    if candidate.error:
        score += 8
        evidence.append("候选请求返回异常信息")

    if stability < 0.6:
        score = max(0, score - 12)
        evidence.append(f"重复请求稳定性较低 ({stability:.2f})")
    elif stability >= 0.9:
        score += 5
        evidence.append(f"重复请求稳定性较高 ({stability:.2f})")

    confidence = _confidence_from_stability(stability)
    risk_level = _risk_from_score(score)
    recommendation = "复核该输入点的服务端处理逻辑，并结合日志与业务上下文确认是否存在输入处理异常。"

    return RiskFinding(
        target_url=target.url,
        method=target.method,
        test_point_name=test_point.name,
        test_point_location=test_point.location,
        risk_level=risk_level,
        confidence=confidence,
        score=score,
        stability=stability,
        recommendation=recommendation,
        evidence=evidence,
        baseline=baseline,
        candidate=candidate,
        difference=difference,
    )
