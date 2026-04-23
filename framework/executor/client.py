from __future__ import annotations

import hashlib
import json
import time
import urllib.parse
import urllib.request
from dataclasses import asdict
from http.cookiejar import CookieJar
from typing import Dict

from framework.config.schema import FrameworkConfig
from framework.executor.cache import ResponseCache
from framework.executor.retry import run_with_retry
from framework.model.finding import ResponseSnapshot
from framework.model.request import TargetRequest
from framework.model.request import TestPoint
from framework.scheduler.rate_limit import HostRequestController

try:
    import httpx  # type: ignore
except Exception:
    httpx = None


class RequestExecutor:
    def __init__(self, config: FrameworkConfig):
        self.config = config
        self.cache = ResponseCache(
            enabled=config.cache.enabled,
            ttl_seconds=config.cache.ttl_seconds,
            max_entries=config.cache.max_entries,
        )
        self.host_controller = HostRequestController(
            requests_per_second=config.rate_limit.requests_per_second,
            per_host=config.concurrency.per_host,
        )
        self.cookie_jar = CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookie_jar))
        self.httpx_client = httpx.Client(follow_redirects=True, timeout=10.0) if httpx is not None else None

    def close(self) -> None:
        if self.httpx_client is not None:
            self.httpx_client.close()

    def _cache_key(self, target: TargetRequest, label: str) -> str:
        serialized = json.dumps({
            "label": label,
            "method": target.method,
            "url": target.url,
            "headers": target.headers,
            "body": target.body,
        }, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _send(self, target: TargetRequest) -> ResponseSnapshot:
        request = urllib.request.Request(
            target.url,
            data=target.body.encode("utf-8") if target.body else None,
            headers=target.headers,
            method=target.method,
        )
        started_at = time.perf_counter()
        try:
            with self.opener.open(request, timeout=10) as response:
                body_bytes = response.read()
                elapsed_ms = int((time.perf_counter() - started_at) * 1000)
                return ResponseSnapshot(
                    status_code=getattr(response, "status", None) or response.getcode(),
                    headers=dict(response.headers.items()),
                    body=body_bytes.decode("utf-8", errors="replace"),
                    elapsed_ms=elapsed_ms,
                )
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - started_at) * 1000)
            return ResponseSnapshot(status_code=None, headers={}, body="", elapsed_ms=elapsed_ms, error=str(exc))

    def execute(self, target: TargetRequest, label: str) -> ResponseSnapshot:
        key = self._cache_key(target, label)
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        host = urllib.parse.urlsplit(target.url).netloc or "default"
        with self.host_controller.gate(host):
            response = run_with_retry(
                lambda: self._send(target),
                attempts=self.config.retry.attempts,
                backoff_seconds=self.config.retry.backoff_seconds,
                retryable_exceptions=(Exception,),
            )
        self.cache.set(key, response)
        return response

    def build_probe_request(self, target: TargetRequest, test_point: TestPoint, probe_value: str) -> TargetRequest:
        mutated = TargetRequest(
            method=target.method,
            url=target.url,
            headers=dict(target.headers),
            body=target.body,
            source=target.source,
            metadata=dict(target.metadata),
        )
        if test_point.location == "query":
            parsed = urllib.parse.urlsplit(target.url)
            values = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
            values[test_point.name] = [probe_value]
            mutated.url = urllib.parse.urlunsplit(parsed._replace(query=urllib.parse.urlencode(values, doseq=True)))
        elif test_point.location == "body":
            values = urllib.parse.parse_qs(target.body, keep_blank_values=True)
            values[test_point.name] = [probe_value]
            mutated.body = urllib.parse.urlencode(values, doseq=True)
        elif test_point.location == "json":
            try:
                payload = json.loads(target.body)
                path = test_point.path.replace("$.", "").split(".")
                cursor = payload
                for name in path[:-1]:
                    if "[" in name and name.endswith("]"):
                        key, index = name[:-1].split("[")
                        cursor = cursor[key][int(index)]
                    else:
                        cursor = cursor[name]
                leaf = path[-1]
                if "[" in leaf and leaf.endswith("]"):
                    key, index = leaf[:-1].split("[")
                    cursor[key][int(index)] = probe_value
                else:
                    cursor[leaf] = probe_value
                mutated.body = json.dumps(payload, ensure_ascii=False)
            except Exception:
                mutated.body = target.body
        elif test_point.location in {"header", "cookie"}:
            mutated.headers[test_point.name] = probe_value
        elif test_point.location == "uri":
            parsed = urllib.parse.urlsplit(target.url)
            segments = [segment for segment in parsed.path.split("/") if segment]
            index = int(test_point.path.removeprefix("uri[").removesuffix("]"))
            if index < len(segments):
                segments[index] = probe_value
                mutated.url = urllib.parse.urlunsplit(parsed._replace(path="/" + "/".join(segments)))
        elif test_point.location in {"xml", "multipart"}:
            mutated.body = target.body.replace(str(test_point.value), probe_value, 1)
        return mutated
