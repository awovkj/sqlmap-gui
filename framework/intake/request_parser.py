from __future__ import annotations

import urllib.parse
from pathlib import Path
from typing import Iterable, List, Optional

from framework.executor.legacy_sqlmap_adapter import parse_request_file_with_sqlmap
from framework.model.request import TargetRequest


HTTP_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}


def _headers_to_dict(headers: Iterable[tuple[str, str]]) -> dict[str, str]:
    return {str(key): str(value) for key, value in headers}


def parse_request_file(path: str) -> List[TargetRequest]:
    targets = []
    for url, method, data, cookie, headers in parse_request_file_with_sqlmap(path):
        header_map = _headers_to_dict(headers)
        if cookie and "Cookie" not in header_map and "cookie" not in {key.lower() for key in header_map}:
            header_map["Cookie"] = cookie
        targets.append(
            TargetRequest(
                method=(method or "GET").upper(),
                url=url,
                headers=header_map,
                body=data or "",
                source=path,
                metadata={"request_file": path},
            )
        )
    return targets


def _infer_url(text: str, headers: dict[str, str]) -> str:
    first_line = text.splitlines()[0].strip()
    parts = first_line.split()
    target = parts[1] if len(parts) > 1 else "/"
    if target.startswith("http://") or target.startswith("https://"):
        return target
    host = headers.get("Host") or headers.get("host") or "localhost"
    scheme = "https" if ":443" in host else "http"
    return urllib.parse.urljoin(f"{scheme}://{host}", target)


def parse_raw_request(text: str, source: str = "raw") -> TargetRequest:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    head, _, body = normalized.partition("\n\n")
    lines = [line for line in head.split("\n") if line.strip()]
    if not lines:
        raise ValueError("Request text is empty")
    request_line = lines[0].strip()
    method = request_line.split()[0].upper()
    if method not in HTTP_METHODS:
        raise ValueError("Unsupported request line")
    headers = {}
    for line in lines[1:]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        headers[key.strip()] = value.strip()
    url = _infer_url(normalized, headers)
    return TargetRequest(method=method, url=url, headers=headers, body=body, source=source)


def parse_target_input(value: str, source: Optional[str] = None) -> List[TargetRequest]:
    text = (value or "").strip()
    if not text:
        return []
    file_path = Path(text)
    if source == "request_file" or (file_path.exists() and file_path.is_file() and file_path.suffix.lower() == ".txt"):
        try:
            return parse_request_file(str(file_path))
        except Exception:
            return [parse_raw_request(file_path.read_text(encoding="utf-8"), source=str(file_path))]
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) == 1 and lines[0].startswith(("http://", "https://")):
        return [TargetRequest(method="GET", url=lines[0], source=source or "direct")]
    if all(line.startswith(("http://", "https://")) for line in lines):
        return [TargetRequest(method="GET", url=line, source=source or "direct") for line in lines]
    return [parse_raw_request(text, source=source or "raw")]
