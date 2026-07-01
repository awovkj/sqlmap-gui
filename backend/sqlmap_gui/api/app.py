from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.sqlmap_gui.api.routes import register_routes
from backend.sqlmap_gui.core.artifacts import ArtifactsManager
from backend.sqlmap_gui.core.paths import ARTIFACTS_DIR, DATA_DIR
from backend.sqlmap_gui.db.database import init_database
from backend.sqlmap_gui.db.repository import Repository
from backend.sqlmap_gui.tasks.events import EventHub
from backend.sqlmap_gui.tasks.manager import TaskManager


def create_app(
    data_dir: Path | None = None,
    artifacts_dir: Path | None = None,
    start_worker: bool = True,
) -> FastAPI:
    data_root = Path(data_dir) if data_dir else DATA_DIR
    artifacts_root = Path(artifacts_dir) if artifacts_dir else ARTIFACTS_DIR
    data_root.mkdir(parents=True, exist_ok=True)
    artifacts_root.mkdir(parents=True, exist_ok=True)

    db_path = data_root / "sqlmap-gui.sqlite3"
    init_database(db_path)
    repo = Repository(db_path)
    repo.ensure_default_project()
    artifacts = ArtifactsManager(artifacts_root)
    hub = EventHub()
    manager = TaskManager(repo, artifacts, hub=hub)

    app = FastAPI(title="SQLmap GUI Backend", version="2.0.0-phase1")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.repo = repo
    app.state.task_manager = manager
    app.state.event_hub = hub
    register_routes(app, repo, manager, hub)
    if start_worker:
        manager.start_background_worker()
    return app
