from pathlib import Path

from backend.sqlmap_gui.db.database import init_database
from backend.sqlmap_gui.db.repository import Repository
from backend.sqlmap_gui.schemas.tasks import ScanConfig


def test_repository_creates_default_project_and_task(tmp_path: Path):
    db_path = tmp_path / "app.sqlite3"
    init_database(db_path)
    repo = Repository(db_path)

    project = repo.ensure_default_project()
    task = repo.create_task(project["id"], ScanConfig(target="http://example.test/?id=1"))
    repo.add_task_event(task["id"], "info", "log", "started")
    repo.finish_task(task["id"], "completed", 0, None)

    tasks = repo.list_tasks()
    events = repo.list_task_events(task["id"])

    assert project["name"] == "Default"
    assert tasks[0]["status"] == "completed"
    assert tasks[0]["exit_code"] == 0
    assert events[0]["message"] == "started"
