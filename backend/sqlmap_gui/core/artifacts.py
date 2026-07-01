from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ArtifactsManager:
    def __init__(self, root: Path):
        self.root = Path(root)

    def task_dir(self, task_id: str) -> Path:
        path = self.root / "tasks" / task_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def sqlmap_output_dir(self, task_id: str) -> Path:
        path = self.task_dir(task_id) / "sqlmap-output"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def reports_dir(self, task_id: str) -> Path:
        path = self.task_dir(task_id) / "reports"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def command_path(self, task_id: str) -> Path:
        return self.task_dir(task_id) / "command.json"

    def log_path(self, task_id: str) -> Path:
        return self.task_dir(task_id) / "run.log"

    def request_path(self, task_id: str) -> Path:
        return self.task_dir(task_id) / "request.txt"

    def write_command(self, task_id: str, command: list[str]) -> Path:
        path = self.command_path(task_id)
        path.write_text(json.dumps(command, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def append_log(self, task_id: str, line: str) -> Path:
        path = self.log_path(task_id)
        with path.open("a", encoding="utf-8", newline="") as handle:
            handle.write(line.rstrip("\n") + "\n")
        return path

    def write_json(self, path: Path, payload: dict[str, Any]) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
