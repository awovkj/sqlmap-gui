from __future__ import annotations

import json
import urllib.parse
from typing import Any, Iterable, List

from framework.model.request import TargetRequest
from framework.model.request import TestPoint


JSON_CONTENT_MARKERS = ("application/json", "+json", "text/json")
XML_CONTENT_MARKERS = ("xml", "soap")
FORM_CONTENT_MARKERS = ("application/x-www-form-urlencoded",)
MULTIPART_MARKERS = ("multipart/form-data",)


def _flatten_json(value: Any, prefix: str = "$") -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, nested in value.items():
            next_prefix = f"{prefix}.{key}"
            yield from _flatten_json(nested, next_prefix)
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            next_prefix = f"{prefix}[{index}]"
            yield from _flatten_json(nested, next_prefix)
    else:
        yield prefix, value


def _content_type(target: TargetRequest) -> str:
    for key, value in target.headers.items():
        if key.lower() == "content-type":
            return value.lower()
    return ""


def _extract_query_points(target: TargetRequest) -> List[TestPoint]:
    parsed = urllib.parse.urlsplit(target.url)
    values = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    items = []
    for key, entries in values.items():
        for index, entry in enumerate(entries):
            items.append(TestPoint(name=key, location="query", value=entry, path=f"query.{key}[{index}]"))
    return items


def _extract_header_points(target: TargetRequest) -> List[TestPoint]:
    items = []
    for key, value in target.headers.items():
        lowered = key.lower()
        if lowered in {"host", "content-length"}:
            continue
        location = "cookie" if lowered == "cookie" else "header"
        items.append(TestPoint(name=key, location=location, value=value, path=f"headers.{key}"))
    return items


def _extract_form_points(target: TargetRequest) -> List[TestPoint]:
    values = urllib.parse.parse_qs(target.body, keep_blank_values=True)
    items = []
    for key, entries in values.items():
        for index, entry in enumerate(entries):
            items.append(TestPoint(name=key, location="body", value=entry, path=f"body.{key}[{index}]", content_type="form"))
    return items


def _extract_json_points(target: TargetRequest) -> List[TestPoint]:
    try:
        loaded = json.loads(target.body)
    except Exception:
        return []
    items = []
    for path, value in _flatten_json(loaded):
        if isinstance(value, (dict, list)):
            continue
        name = path.split(".")[-1].split("[")[0].lstrip("$") or "root"
        items.append(TestPoint(name=name, location="json", value=value, path=path, content_type="json"))
    return items


def _extract_xml_points(target: TargetRequest) -> List[TestPoint]:
    body = target.body or ""
    items = []
    for index, token in enumerate(body.split("<")):
        if ">" not in token:
            continue
        tag, _, remainder = token.partition(">")
        name = tag.split()[0].strip("/")
        text = remainder.split("<", 1)[0].strip()
        if not name or not text:
            continue
        items.append(TestPoint(name=name, location="xml", value=text, path=f"xml.{name}[{index}]", content_type="xml"))
    return items


def _extract_multipart_points(target: TargetRequest) -> List[TestPoint]:
    body = target.body or ""
    items = []
    for chunk in body.split("Content-Disposition:"):
        if "name=" not in chunk:
            continue
        name = chunk.split("name=", 1)[1].splitlines()[0].strip().strip('";')
        payload = chunk.split("\n\n", 1)[1] if "\n\n" in chunk else ""
        value = payload.splitlines()[0].strip() if payload else ""
        items.append(TestPoint(name=name, location="multipart", value=value, path=f"multipart.{name}", content_type="multipart"))
    return items


def _extract_uri_point(target: TargetRequest) -> List[TestPoint]:
    parsed = urllib.parse.urlsplit(target.url)
    path = parsed.path or "/"
    items = []
    for index, segment in enumerate(part for part in path.split("/") if part):
        items.append(TestPoint(name=f"segment_{index}", location="uri", value=segment, path=f"uri[{index}]"))
    return items


def extract_test_points(target: TargetRequest) -> List[TestPoint]:
    points: List[TestPoint] = []
    points.extend(_extract_query_points(target))
    points.extend(_extract_header_points(target))
    points.extend(_extract_uri_point(target))

    content_type = _content_type(target)
    if target.body:
        if any(marker in content_type for marker in JSON_CONTENT_MARKERS):
            points.extend(_extract_json_points(target))
        elif any(marker in content_type for marker in XML_CONTENT_MARKERS):
            points.extend(_extract_xml_points(target))
        elif any(marker in content_type for marker in MULTIPART_MARKERS):
            points.extend(_extract_multipart_points(target))
        elif any(marker in content_type for marker in FORM_CONTENT_MARKERS) or "=" in target.body:
            points.extend(_extract_form_points(target))
        else:
            points.append(TestPoint(name="body", location="body", value=target.body, path="body.raw", content_type="text"))

    seen = set()
    unique_points = []
    for point in points:
        key = (point.location, point.path, str(point.value))
        if key in seen:
            continue
        seen.add(key)
        unique_points.append(point)
    return unique_points
