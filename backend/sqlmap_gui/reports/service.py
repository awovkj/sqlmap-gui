from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from backend.sqlmap_gui.core.artifacts import ArtifactsManager


class ReportService:
    def __init__(self, artifacts: ArtifactsManager):
        self.artifacts = artifacts

    def create_basic_report(self, task: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
        task_id = task["id"]
        reports_dir = self.artifacts.reports_dir(task_id)
        log_lines = [event["message"] for event in events if event.get("type") == "log"]
        summary = {
            "task_id": task_id,
            "target": task["target"],
            "status": task["status"],
            "exit_code": task.get("exit_code"),
            "log_lines": len(log_lines),
            "last_log_line": log_lines[-1] if log_lines else "",
        }

        json_path = reports_dir / "report.json"
        html_path = reports_dir / "report.html"
        markdown_path = reports_dir / "report.md"

        self.artifacts.write_json(json_path, summary)
        html_path.write_text(
            "<!doctype html><meta charset='utf-8'>"
            f"<title>SQLmap GUI Report {html.escape(task_id)}</title>"
            f"<h1>SQLmap GUI Report</h1><p><b>Target:</b> {html.escape(task['target'])}</p>"
            f"<p><b>Status:</b> {html.escape(task['status'])}</p>"
            f"<p><b>Exit code:</b> {html.escape(str(task.get('exit_code')))}</p>"
            f"<pre>{html.escape(chr(10).join(log_lines[-200:]))}</pre>",
            encoding="utf-8",
        )
        markdown_path.write_text(
            "\n".join(
                [
                    "# SQLmap GUI Report",
                    "",
                    f"- Task: `{task_id}`",
                    f"- Target: `{task['target']}`",
                    f"- Status: `{task['status']}`",
                    f"- Exit code: `{task.get('exit_code')}`",
                    "",
                    "## Last log lines",
                    "",
                    "```text",
                    "\n".join(log_lines[-200:]),
                    "```",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        return {
            "summary": summary,
            "json_path": str(json_path),
            "html_path": str(html_path),
            "markdown_path": str(markdown_path),
        }
