from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.sqlmap_gui.schemas.tasks import ScanConfig, TaskStatus


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


class Repository:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def ensure_default_project(self) -> dict[str, Any]:
        now = utc_now()
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM projects WHERE name = ?", ("Default",)).fetchone()
            if row:
                return dict(row)
            project_id = _new_id("project")
            connection.execute(
                """
                INSERT INTO projects (id, name, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (project_id, "Default", "Default project", now, now),
            )
            connection.commit()
            return dict(connection.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone())

    def create_task(self, project_id: str, config: ScanConfig) -> dict[str, Any]:
        now = utc_now()
        task_id = _new_id("task")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO tasks (
                    id, project_id, target_id, status, engine, config_json, command_json,
                    output_dir, target, input_type, created_at, updated_at
                )
                VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    project_id,
                    TaskStatus.QUEUED.value,
                    "sqlmap",
                    config.model_dump_json(),
                    "[]",
                    "",
                    config.target,
                    config.input_type,
                    now,
                    now,
                ),
            )
            connection.commit()
        return self.get_task(task_id)

    def get_task(self, task_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            raise KeyError(f"Task not found: {task_id}")
        return dict(row)

    def list_tasks(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM tasks ORDER BY created_at DESC").fetchall()
        return [dict(row) for row in rows]

    def list_queued_tasks(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM tasks WHERE status = ? ORDER BY created_at ASC",
                (TaskStatus.QUEUED.value,),
            ).fetchall()
        return [dict(row) for row in rows]

    def update_task_runtime(
        self,
        task_id: str,
        *,
        status: str,
        command: list[str] | None = None,
        output_dir: str | None = None,
        started_at: str | None = None,
        error_message: str | None = None,
    ) -> dict[str, Any]:
        existing = self.get_task(task_id)
        now = utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE tasks
                SET status = ?, command_json = ?, output_dir = ?, started_at = COALESCE(?, started_at),
                    error_message = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    json.dumps(command if command is not None else json.loads(existing["command_json"])),
                    output_dir if output_dir is not None else existing["output_dir"],
                    started_at,
                    error_message,
                    now,
                    task_id,
                ),
            )
            connection.commit()
        return self.get_task(task_id)

    def finish_task(self, task_id: str, status: str, exit_code: int | None, error_message: str | None) -> dict[str, Any]:
        now = utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE tasks
                SET status = ?, exit_code = ?, error_message = ?, finished_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, exit_code, error_message, now, now, task_id),
            )
            connection.commit()
        return self.get_task(task_id)

    def add_task_event(self, task_id: str, level: str, event_type: str, message: str) -> dict[str, Any]:
        now = utc_now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO task_events (task_id, level, type, message, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (task_id, level, event_type, message, now),
            )
            connection.commit()
            row = connection.execute("SELECT * FROM task_events WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return dict(row)

    def list_task_events(self, task_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM task_events WHERE task_id = ? ORDER BY id ASC",
                (task_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def create_report(
        self,
        task_id: str,
        summary: dict[str, Any],
        json_path: str,
        html_path: str,
        markdown_path: str,
    ) -> dict[str, Any]:
        now = utc_now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO reports (task_id, summary_json, json_path, html_path, markdown_path, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    summary_json = excluded.summary_json,
                    json_path = excluded.json_path,
                    html_path = excluded.html_path,
                    markdown_path = excluded.markdown_path,
                    created_at = excluded.created_at
                """,
                (task_id, json.dumps(summary, ensure_ascii=False), json_path, html_path, markdown_path, now),
            )
            connection.commit()
        return self.get_report_for_task(task_id)

    def get_report_for_task(self, task_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM reports WHERE task_id = ?", (task_id,)).fetchone()
        if not row:
            raise KeyError(f"Report not found for task: {task_id}")
        return dict(row)
