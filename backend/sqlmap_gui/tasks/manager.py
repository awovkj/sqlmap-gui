from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from backend.sqlmap_gui.core.artifacts import ArtifactsManager
from backend.sqlmap_gui.core.paths import PROJECT_ROOT, VENDOR_SQLMAP_SCRIPT
from backend.sqlmap_gui.db.repository import Repository, utc_now
from backend.sqlmap_gui.engine.command_builder import build_sqlmap_command
from backend.sqlmap_gui.engine.subprocess_engine import SubprocessSqlmapEngine
from backend.sqlmap_gui.reports.service import ReportService
from backend.sqlmap_gui.schemas.tasks import ScanConfig, TaskStatus
from backend.sqlmap_gui.tasks.events import EventHub


class TaskManager:
    def __init__(
        self,
        repo: Repository,
        artifacts: ArtifactsManager,
        engine: Any | None = None,
        hub: EventHub | None = None,
        max_workers: int = 2,
        sqlmap_script: Path = VENDOR_SQLMAP_SCRIPT,
    ) -> None:
        self.repo = repo
        self.artifacts = artifacts
        self.engine = engine or SubprocessSqlmapEngine()
        self.hub = hub or EventHub()
        self.sqlmap_script = Path(sqlmap_script)
        self.report_service = ReportService(artifacts)
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._cancel_events: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def create_task(self, project_id: str, config: ScanConfig) -> dict[str, Any]:
        task = self.repo.create_task(project_id, config)
        self.hub.publish("status", task["id"], "queued", status=TaskStatus.QUEUED.value)
        return task

    def start_background_worker(self) -> None:
        thread = threading.Thread(target=self._worker_loop, daemon=True)
        thread.start()

    def _worker_loop(self) -> None:
        while True:
            self.run_pending_once()
            threading.Event().wait(1.0)

    def run_pending_once(self) -> None:
        queued = self.repo.list_queued_tasks()
        for task in queued:
            self._run_task(task)

    def cancel_task(self, task_id: str) -> dict[str, Any]:
        with self._lock:
            event = self._cancel_events.get(task_id)
            if event:
                event.set()
        task = self.repo.update_task_runtime(task_id, status=TaskStatus.CANCELLING.value)
        self.hub.publish("status", task_id, "cancelling", status=TaskStatus.CANCELLING.value)
        return task

    def _prepare_config(self, task_id: str, config: ScanConfig) -> ScanConfig:
        if config.input_type != "raw_request":
            return config
        request_path = self.artifacts.request_path(task_id)
        request_path.write_text(config.target, encoding="utf-8", newline="")
        return config.model_copy(update={"request_file": str(request_path)})

    def _run_task(self, task: dict[str, Any]) -> None:
        task_id = task["id"]
        cancel_event = threading.Event()
        with self._lock:
            self._cancel_events[task_id] = cancel_event

        config = ScanConfig.model_validate(json.loads(task["config_json"]))
        config = self._prepare_config(task_id, config)
        task_dir = self.artifacts.task_dir(task_id)
        sqlmap_output = self.artifacts.sqlmap_output_dir(task_id)
        command = build_sqlmap_command(config, self.sqlmap_script, sqlmap_output)
        self.artifacts.write_command(task_id, command)
        self.repo.update_task_runtime(
            task_id,
            status=TaskStatus.RUNNING.value,
            command=command,
            output_dir=str(task_dir),
            started_at=utc_now(),
        )
        self.hub.publish("status", task_id, "running", status=TaskStatus.RUNNING.value)

        def on_line(line: str) -> None:
            self.artifacts.append_log(task_id, line)
            self.repo.add_task_event(task_id, "info", "log", line)
            self.hub.publish("log", task_id, line)

        try:
            exit_code = self.engine.run(command, PROJECT_ROOT, on_line, cancel_event)
            final_status = TaskStatus.CANCELLED.value if cancel_event.is_set() else (
                TaskStatus.COMPLETED.value if exit_code == 0 else TaskStatus.FAILED.value
            )
            finished = self.repo.finish_task(task_id, final_status, exit_code, None if exit_code == 0 else "sqlmap failed")
        except Exception as exc:
            self.artifacts.append_log(task_id, f"[ERROR] {exc}")
            self.repo.add_task_event(task_id, "error", "error", str(exc))
            finished = self.repo.finish_task(task_id, TaskStatus.FAILED.value, None, str(exc))

        events = self.repo.list_task_events(task_id)
        report = self.report_service.create_basic_report(finished, events)
        self.repo.create_report(task_id, report["summary"], report["json_path"], report["html_path"], report["markdown_path"])
        self.hub.publish("status", task_id, finished["status"], status=finished["status"])
        with self._lock:
            self._cancel_events.pop(task_id, None)
