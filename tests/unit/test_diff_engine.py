from framework.analyzer.diff_engine import compare_responses
from framework.config.schema import AnalyzerConfig
from framework.model.finding import ResponseSnapshot


def test_response_comparison_detects_changes():
    config = AnalyzerConfig(indicator_keywords=["error", "warning"])
    baseline = ResponseSnapshot(status_code=200, body="ok")
    candidate = ResponseSnapshot(status_code=500, body="error happened")
    diff = compare_responses(baseline, candidate, config)
    assert diff.status_changed is True
    assert diff.length_delta > 0
    assert "error" in diff.added_keywords
