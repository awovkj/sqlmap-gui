from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
VENDOR_SQLMAP_DIR = PROJECT_ROOT / "vendor" / "sqlmap"
VENDOR_SQLMAP_SCRIPT = VENDOR_SQLMAP_DIR / "sqlmap.py"


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
