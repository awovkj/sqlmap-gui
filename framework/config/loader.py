from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional

from framework.config.defaults import clone_defaults
from framework.config.schema import AnalyzerConfig
from framework.config.schema import CacheConfig
from framework.config.schema import ConcurrencyConfig
from framework.config.schema import FrameworkConfig
from framework.config.schema import LoggingConfig
from framework.config.schema import OutputConfig
from framework.config.schema import RateLimitConfig
from framework.config.schema import RetryConfig
from framework.config.schema import TargetConfig

try:
    import yaml  # type: ignore
except Exception:
    yaml = None


ENV_PREFIX = "FRAMEWORK__"


def deep_merge(base: Dict[str, Any], override: Mapping[str, Any]) -> Dict[str, Any]:
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(base.get(key), dict):
            deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _coerce_env_value(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        pass
    try:
        return json.loads(value)
    except Exception:
        return value


def apply_env_overrides(config: Dict[str, Any], environ: Optional[Mapping[str, str]] = None) -> Dict[str, Any]:
    source = environ or os.environ
    for key, value in source.items():
        if not key.startswith(ENV_PREFIX):
            continue
        parts = [part.lower() for part in key[len(ENV_PREFIX):].split("__") if part]
        if not parts:
            continue
        cursor = config
        for part in parts[:-1]:
            cursor = cursor.setdefault(part, {})
        cursor[parts[-1]] = _coerce_env_value(value)
    return config


def _read_config_file(path: str) -> Dict[str, Any]:
    file_path = Path(path)
    raw = file_path.read_text(encoding="utf-8")
    suffix = file_path.suffix.lower()
    if suffix == ".json":
        return json.loads(raw)
    if suffix in {".yaml", ".yml"}:
        if yaml is None:
            raise RuntimeError("YAML support requires PyYAML")
        loaded = yaml.safe_load(raw)
        return loaded or {}
    raise ValueError(f"Unsupported config format: {file_path.suffix}")


def _normalize_headers(value: Any) -> Dict[str, str]:
    if not value:
        return {}
    if isinstance(value, dict):
        return {str(k): str(v) for k, v in value.items()}
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        headers = {}
        for item in value:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                headers[str(item[0])] = str(item[1])
        return headers
    return {}


def _build_targets(raw_targets: Any) -> list[TargetConfig]:
    targets = []
    for item in raw_targets or []:
        if isinstance(item, str):
            targets.append(TargetConfig(url=item))
            continue
        if not isinstance(item, Mapping):
            continue
        targets.append(
            TargetConfig(
                url=item.get("url"),
                request_file=item.get("request_file") or item.get("requestFile"),
                method=str(item.get("method") or "GET").upper(),
                headers=_normalize_headers(item.get("headers")),
                body=str(item.get("body") or ""),
                source=str(item.get("source") or "config"),
            )
        )
    return targets


def build_config(raw: Mapping[str, Any]) -> FrameworkConfig:
    concurrency = raw.get("concurrency", {}) or {}
    retry = raw.get("retry", {}) or {}
    rate_limit = raw.get("rate_limit", {}) or {}
    cache = raw.get("cache", {}) or {}
    analyzer = raw.get("analyzer", {}) or {}
    logging = raw.get("logging", {}) or {}
    output = raw.get("output", {}) or {}

    return FrameworkConfig(
        targets=_build_targets(raw.get("targets")),
        concurrency=ConcurrencyConfig(
            workers=max(1, int(concurrency.get("workers", 8))),
            per_host=max(1, int(concurrency.get("per_host", 2))),
        ),
        retry=RetryConfig(
            attempts=max(1, int(retry.get("attempts", 2))),
            backoff_seconds=max(0.0, float(retry.get("backoff_seconds", 0.5))),
        ),
        rate_limit=RateLimitConfig(
            requests_per_second=max(0.0, float(rate_limit.get("requests_per_second", 2.0))),
        ),
        cache=CacheConfig(
            enabled=bool(cache.get("enabled", True)),
            ttl_seconds=max(0, int(cache.get("ttl_seconds", 300))),
            max_entries=max(1, int(cache.get("max_entries", 512))),
        ),
        analyzer=AnalyzerConfig(
            length_delta_threshold=max(0, int(analyzer.get("length_delta_threshold", 24))),
            similarity_threshold=max(0.0, min(1.0, float(analyzer.get("similarity_threshold", 0.92)))),
            repeat_count=max(1, int(analyzer.get("repeat_count", 2))),
            indicator_keywords=[str(item) for item in analyzer.get("indicator_keywords", [])],
        ),
        logging=LoggingConfig(
            level=str(logging.get("level", "INFO")).upper(),
            redact_fields=[str(item).lower() for item in logging.get("redact_fields", [])],
        ),
        output=OutputConfig(
            directory=str(output.get("directory", "artifacts/security-assessment")),
            json_report=str(output.get("json_report", "assessment.json")),
            html_report=str(output.get("html_report", "assessment.html")),
        ),
        plugins=[str(item) for item in raw.get("plugins", [])],
    )


def load_config(
    config_path: Optional[str] = None,
    inline: Optional[Mapping[str, Any]] = None,
    cli_overrides: Optional[Mapping[str, Any]] = None,
    environ: Optional[Mapping[str, str]] = None,
) -> FrameworkConfig:
    raw = clone_defaults()
    if config_path:
        deep_merge(raw, _read_config_file(config_path))
    if inline:
        deep_merge(raw, dict(inline))
    apply_env_overrides(raw, environ=environ)
    if cli_overrides:
        deep_merge(raw, dict(cli_overrides))
    return build_config(raw)
