from __future__ import annotations

import copy

DEFAULT_CONFIG = {
    "targets": [],
    "concurrency": {
        "workers": 8,
        "per_host": 2,
    },
    "retry": {
        "attempts": 2,
        "backoff_seconds": 0.5,
    },
    "rate_limit": {
        "requests_per_second": 2.0,
    },
    "cache": {
        "enabled": True,
        "ttl_seconds": 300,
        "max_entries": 512,
    },
    "analyzer": {
        "length_delta_threshold": 24,
        "similarity_threshold": 0.92,
        "repeat_count": 2,
        "indicator_keywords": [
            "error",
            "exception",
            "invalid",
            "failed",
            "warning",
            "stack trace",
            "denied",
            "forbidden",
        ],
    },
    "logging": {
        "level": "INFO",
        "redact_fields": ["authorization", "cookie", "set-cookie", "token", "password", "apikey", "api-key"],
    },
    "output": {
        "directory": "artifacts/security-assessment",
        "json_report": "assessment.json",
        "html_report": "assessment.html",
    },
    "plugins": [],
}


def clone_defaults() -> dict:
    return copy.deepcopy(DEFAULT_CONFIG)
