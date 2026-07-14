import threading
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
        on_line("[INFO] fetching database names")
        on_line("available databases [1]:")
        on_line("[*] security")
        on_line("[INFO] scan completed")
        return 0


class ReportFailingTaskManager(TaskManager):
    def generate_report(self, task_id: str):
        raise RuntimeError("report parser failed")


def test_task_manager_runs_task_and_writes_report(tmp_path: Path):
    db_path = tmp_path / "app.sqlite3"
    init_database(db_path)
    repo = Repository(db_path)
    artifacts = ArtifactsManager(tmp_path / "artifacts")
    hub = EventHub()
    manager = TaskManager(repo, artifacts, FakeEngine(), hub, max_workers=1)
    project = repo.ensure_default_project()

    task = manager.create_task(project["id"], ScanConfig(target="http://example.test/?id=1"))
    for future in manager.run_pending_once():
        future.result()

    stored = repo.get_task(task["id"])
    report = repo.get_report_for_task(task["id"])
    log_text = Path(stored["output_dir"], "run.log").read_text(encoding="utf-8")

    assert stored["status"] == "completed"
    assert "scan completed" in log_text
    assert report["summary_json"]
    assert '"security"' in report["summary_json"]
    assert hub.snapshot()[-1]["type"] == "status"


def test_report_generation_failure_does_not_override_completed_task(tmp_path: Path):
    db_path = tmp_path / "app.sqlite3"
    init_database(db_path)
    repo = Repository(db_path)
    artifacts = ArtifactsManager(tmp_path / "artifacts")
    hub = EventHub()
    manager = ReportFailingTaskManager(repo, artifacts, FakeEngine(), hub, max_workers=1)
    project = repo.ensure_default_project()

    task = manager.create_task(project["id"], ScanConfig(target="http://example.test/?id=1"))
    for future in manager.run_pending_once():
        future.result()

    stored = repo.get_task(task["id"])
    events = repo.list_task_events(task["id"])

    assert stored["status"] == "completed"
    assert any(event["type"] == "error" and "report parser failed" in event["message"] for event in events)


class BlockingEngine:
    """Both concurrent runs must meet at the barrier, proving they overlap."""

    def __init__(self, barrier: threading.Barrier):
        self.barrier = barrier

    def run(self, command, cwd, on_line, cancel_event):
        self.barrier.wait(timeout=5)
        on_line("[INFO] scan completed")
        return 0


class PrologueFailingManager(TaskManager):
    def _prepare_config(self, task_id, config):
        raise RuntimeError("prepare failed")


def test_task_manager_runs_two_tasks_concurrently(tmp_path: Path):
    db_path = tmp_path / "app.sqlite3"
    init_database(db_path)
    repo = Repository(db_path)
    artifacts = ArtifactsManager(tmp_path / "artifacts")
    hub = EventHub()
    barrier = threading.Barrier(2)
    manager = TaskManager(repo, artifacts, BlockingEngine(barrier), hub, max_workers=2)
    project = repo.ensure_default_project()

    manager.create_task(project["id"], ScanConfig(target="http://a.test/?id=1"))
    manager.create_task(project["id"], ScanConfig(target="http://b.test/?id=1"))
    futures = manager.run_pending_once()

    assert len(futures) == 2
    for future in futures:
        future.result(timeout=10)  # would hang if the runs were serial

    assert {task["status"] for task in repo.list_tasks()} == {"completed"}
    # A repeat poll must not re-dispatch already-finished tasks.
    assert manager.run_pending_once() == []


def test_prologue_failure_marks_task_failed_and_clears_inflight(tmp_path: Path):
    db_path = tmp_path / "app.sqlite3"
    init_database(db_path)
    repo = Repository(db_path)
    artifacts = ArtifactsManager(tmp_path / "artifacts")
    hub = EventHub()
    manager = PrologueFailingManager(repo, artifacts, FakeEngine(), hub, max_workers=1)
    project = repo.ensure_default_project()

    task = manager.create_task(project["id"], ScanConfig(target="http://x.test/?id=1"))
    for future in manager.run_pending_once():
        future.result(timeout=10)

    stored = repo.get_task(task["id"])
    assert stored["status"] == "failed"
    assert task["id"] not in manager._inflight
    assert manager.run_pending_once() == []
