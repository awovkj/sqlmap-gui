from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from backend.sqlmap_gui.db.repository import Repository
from backend.sqlmap_gui.schemas.tasks import ScanConfig
from backend.sqlmap_gui.tasks.events import EventHub
from backend.sqlmap_gui.tasks.manager import TaskManager


def _serialize_task(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": task["id"],
        "project_id": task["project_id"],
        "status": task["status"],
        "engine": task["engine"],
        "command": json.loads(task["command_json"]),
        "output_dir": task["output_dir"],
        "target": task["target"],
        "input_type": task["input_type"],
        "started_at": task["started_at"],
        "finished_at": task["finished_at"],
        "exit_code": task["exit_code"],
        "error_message": task["error_message"],
    }


def register_routes(app: FastAPI, repo: Repository, manager: TaskManager, hub: EventHub) -> None:
    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "service": "sqlmap-gui-backend"}

    @app.get("/api/tasks")
    def list_tasks() -> list[dict[str, Any]]:
        return [_serialize_task(task) for task in repo.list_tasks()]

    @app.post("/api/tasks")
    def create_task(config: ScanConfig) -> dict[str, Any]:
        project = repo.ensure_default_project()
        return _serialize_task(manager.create_task(project["id"], config))

    @app.post("/api/tasks/batch")
    def create_batch(configs: list[ScanConfig]) -> list[dict[str, Any]]:
        project = repo.ensure_default_project()
        return [_serialize_task(manager.create_task(project["id"], config)) for config in configs]

    @app.get("/api/tasks/{task_id}")
    def get_task(task_id: str) -> dict[str, Any]:
        try:
            return _serialize_task(repo.get_task(task_id))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/tasks/{task_id}/cancel")
    def cancel_task(task_id: str) -> dict[str, Any]:
        try:
            return _serialize_task(manager.cancel_task(task_id))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/tasks/{task_id}/logs")
    def get_task_logs(task_id: str) -> list[dict[str, Any]]:
        return repo.list_task_events(task_id)

    @app.get("/api/tasks/{task_id}/report")
    def get_task_report(task_id: str) -> dict[str, Any]:
        try:
            report = repo.get_report_for_task(task_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        report["summary"] = json.loads(report.pop("summary_json"))
        return report

    @app.get("/api/events")
    async def events() -> StreamingResponse:
        async def stream():
            last_id = 0
            while True:
                for event in hub.snapshot(last_id):
                    last_id = int(event["id"])
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                await asyncio.sleep(1.0)

        return StreamingResponse(stream(), media_type="text/event-stream")
