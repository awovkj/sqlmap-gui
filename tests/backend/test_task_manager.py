from pathlib import Path

from backend.sqlmap_gui.core.artifacts import ArtifactsManager
from backend.sqlmap_gui.db.database import init_database
from backend.sqlmap_gui.db.repository import Repository
from backend.sqlmap_gui.schemas.tasks import ScanConfig
from backend.sqlmap_gui.tasks.events import EventHub
from backend.sqlmap_gui.tasks.manager import TaskManager


class FakeEngine:
    def run(self, command, cwd, on_line, cancel_event):
        on_line("[INFO] testing target")
        on_line("[INFO] scan completed")
        return 0


def test_task_manager_runs_task_and_writes_report(tmp_path: Path):
    db_path = tmp_path / "app.sqlite3"
    init_database(db_path)
    repo = Repository(db_path)
    artifacts = ArtifactsManager(tmp_path / "artifacts")
    hub = EventHub()
    manager = TaskManager(repo, artifacts, FakeEngine(), hub, max_workers=1)
    project = repo.ensure_default_project()

    task = manager.create_task(project["id"], ScanConfig(target="http://example.test/?id=1"))
    manager.run_pending_once()

    stored = repo.get_task(task["id"])
    report = repo.get_report_for_task(task["id"])
    log_text = Path(stored["output_dir"], "run.log").read_text(encoding="utf-8")

    assert stored["status"] == "completed"
    assert "scan completed" in log_text
    assert report["json_path"].endswith("report.json")
    assert hub.snapshot()[-1]["type"] == "status"
