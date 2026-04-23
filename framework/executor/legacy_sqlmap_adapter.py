from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Tuple


def _sqlmap_root() -> str:
    return str(Path(__file__).resolve().parents[2] / "sqlmap")


def bootstrap_sqlmap_path() -> None:
    root = _sqlmap_root()
    if root not in sys.path:
        sys.path.insert(0, root)


def parse_request_file_with_sqlmap(path: str) -> List[Tuple[str, str, str | None, str | None, tuple]]:
    bootstrap_sqlmap_path()
    from lib.core.common import parseRequestFile  # type: ignore

    return list(parseRequestFile(path))


def sqlmap_available() -> bool:
    return os.path.isfile(os.path.join(_sqlmap_root(), "sqlmap.py"))
