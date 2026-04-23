from __future__ import annotations

from difflib import SequenceMatcher

from framework.config.schema import AnalyzerConfig
from framework.model.finding import ResponseDifference
from framework.model.finding import ResponseSnapshot
from framework.analyzer.keyword_rules import keyword_hits


def compare_responses(
    baseline: ResponseSnapshot,
    candidate: ResponseSnapshot,
    config: AnalyzerConfig,
) -> ResponseDifference:
    baseline_body = baseline.body or ""
    candidate_body = candidate.body or ""
    similarity = SequenceMatcher(None, baseline_body, candidate_body).ratio() if baseline_body or candidate_body else 1.0
    baseline_keywords = keyword_hits(baseline_body, config.indicator_keywords)
    candidate_keywords = keyword_hits(candidate_body, config.indicator_keywords)
    return ResponseDifference(
        status_changed=baseline.status_code != candidate.status_code,
        length_delta=abs(len(candidate_body) - len(baseline_body)),
        similarity=similarity,
        added_keywords=sorted(candidate_keywords - baseline_keywords),
        removed_keywords=sorted(baseline_keywords - candidate_keywords),
        baseline_length=len(baseline_body),
        candidate_length=len(candidate_body),
        error_changed=(baseline.error or "") != (candidate.error or ""),
    )
