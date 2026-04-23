from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TargetConfig:
    url: Optional[str] = None
    request_file: Optional[str] = None
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)
    body: str = ""
    source: str = "config"


@dataclass
class ConcurrencyConfig:
    workers: int = 8
    per_host: int = 2


@dataclass
class RetryConfig:
    attempts: int = 2
    backoff_seconds: float = 0.5


@dataclass
class RateLimitConfig:
    requests_per_second: float = 2.0


@dataclass
class CacheConfig:
    enabled: bool = True
    ttl_seconds: int = 300
    max_entries: int = 512


@dataclass
class AnalyzerConfig:
    length_delta_threshold: int = 24
    similarity_threshold: float = 0.92
    repeat_count: int = 2
    indicator_keywords: List[str] = field(default_factory=list)


@dataclass
class LoggingConfig:
    level: str = "INFO"
    redact_fields: List[str] = field(default_factory=list)


@dataclass
class OutputConfig:
    directory: str = "artifacts/security-assessment"
    json_report: str = "assessment.json"
    html_report: str = "assessment.html"


@dataclass
class FrameworkConfig:
    targets: List[TargetConfig] = field(default_factory=list)
    concurrency: ConcurrencyConfig = field(default_factory=ConcurrencyConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    analyzer: AnalyzerConfig = field(default_factory=AnalyzerConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    plugins: List[str] = field(default_factory=list)
