from __future__ import annotations

from typing import Iterable, Set


def keyword_hits(text: str, keywords: Iterable[str]) -> Set[str]:
    haystack = (text or "").lower()
    return {keyword for keyword in keywords if keyword and keyword.lower() in haystack}
