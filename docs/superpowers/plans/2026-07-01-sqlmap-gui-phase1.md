# SQLmap GUI Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 1 core platform loop: Electron launches a React workbench and Python FastAPI backend; users can create a sqlmap task, stream logs, persist history, and receive a basic report artifact.

**Architecture:** The desktop app is split into `apps/desktop` for Electron, `apps/web` for React, and `backend/sqlmap_gui` for FastAPI, SQLite, task orchestration, and sqlmap subprocess execution. sqlmap core is synced into `vendor/sqlmap` from `C:\Users\31373\Downloads\sqlmap-master`; the backend invokes it through a `SubprocessSqlmapEngine` behind a command-builder boundary.

**Tech Stack:** Python 3.12, FastAPI, Uvicorn, SQLite, pytest, Electron, React, TypeScript, Vite, Tailwind-compatible CSS utility layout.

---

## File Structure

- Create `package.json`: root Node scripts for web build, Electron start, and combined dev start.
- Create `tsconfig.json`: TypeScript project settings.
- Create `apps/desktop/main.cjs`: Electron main process and Python backend lifecycle manager.
- Create `apps/web/index.html`: Vite HTML entry.
- Create `apps/web/src/main.tsx`: React bootstrap.
- Create `apps/web/src/App.tsx`: Phase 1 professional workbench UI.
- Create `apps/web/src/api.ts`: REST and SSE client functions.
- Create `apps/web/src/types.ts`: shared frontend DTO types.
- Create `apps/web/src/styles.css`: polished workbench styling.
- Create `requirements.txt`: Python backend runtime dependencies.
- Create `backend/sqlmap_gui/**`: FastAPI backend package.
- Create `tests/backend/**`: pytest tests for command building, repository, task manager, and API.
- Create `vendor/sqlmap/`: synchronized copy of `C:\Users\31373\Downloads\sqlmap-master`.
- Keep legacy `GUI-CN/`, `framework/`, and old `sqlmap/` in place during Phase 1; they stop being default entry points but are not deleted in this plan.

## Task 1: Project Manifests and Baseline

**Files:**
- Create: `package.json`
- Create: `tsconfig.json`
- Create: `requirements.txt`
- Create: `backend/sqlmap_gui/__init__.py`
- Create: `backend/sqlmap_gui/main.py`
- Test: existing `tests/unit/*.py`

- [ ] **Step 1: Write root Node and Python manifests**

Create `package.json` with these exact scripts and dependencies:

```json
{
  "name": "sqlmap-gui",
  "version": "2.0.0-phase1",
  "private": true,
  "description": "Modern Electron + FastAPI SQLmap GUI",
  "main": "apps/desktop/main.cjs",
  "scripts": {
    "start": "node scripts/start-dev.cjs",
    "build:web": "vite build apps/web",
    "typecheck": "tsc --noEmit",
    "test:backend": "python -m pytest tests/backend -q",
    "test:legacy": "python -m pytest tests/unit -q"
  },
  "dependencies": {
    "@vitejs/plugin-react": "^4.3.4",
    "electron": "^33.2.1",
    "vite": "^6.0.3",
    "typescript": "^5.7.2",
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1"
  }
}
```

Create `requirements.txt`:

```text
fastapi>=0.115
uvicorn[standard]>=0.30
pydantic>=2
pytest>=8
httpx>=0.27
```

Create `backend/sqlmap_gui/main.py` temporarily:

```python
from backend.sqlmap_gui.api.app import create_app

app = create_app()
```

- [ ] **Step 2: Run existing baseline tests**

Run:

```powershell
python -m pytest tests/unit -q
```

Expected: `3 passed`.

- [ ] **Step 3: Commit manifests after backend package imports exist**

Run:

```powershell
git add package.json tsconfig.json requirements.txt backend/sqlmap_gui/__init__.py backend/sqlmap_gui/main.py
git commit -m "chore: scaffold phase1 manifests"
```

Expected: commit succeeds.

## Task 2: Backend Paths, Schemas, and Command Builder

**Files:**
- Create: `backend/sqlmap_gui/core/paths.py`
- Create: `backend/sqlmap_gui/schemas/tasks.py`
- Create: `backend/sqlmap_gui/engine/command_builder.py`
- Create: `tests/backend/test_command_builder.py`

- [ ] **Step 1: Write failing command builder tests**

Create `tests/backend/test_command_builder.py`:

```python
from pathlib import Path

from backend.sqlmap_gui.engine.command_builder import build_sqlmap_command
from backend.sqlmap_gui.schemas.tasks import ScanConfig


def test_builds_url_task_command_with_defaults(tmp_path: Path):
    config = ScanConfig(target="http://127.0.0.1/?id=1", input_type="url")
    command = build_sqlmap_command(config, Path("vendor/sqlmap/sqlmap.py"), tmp_path)

    assert command[:3] == ["python", "-u", "vendor/sqlmap/sqlmap.py"]
    assert command[3:] == [
        "-u", "http://127.0.0.1/?id=1",
        "--batch",
        "--random-agent",
        "--level", "3",
        "--risk", "2",
        "--threads", "6",
        "--eta",
        "--parse-errors",
        "--output-dir", str(tmp_path),
    ]


def test_builds_raw_request_command_with_extra_args(tmp_path: Path):
    request_file = tmp_path / "request.txt"
    config = ScanConfig(
        target="POST /login HTTP/1.1\\nHost: example.test\\n\\na=1",
        input_type="raw_request",
        request_file=str(request_file),
        preset="waf",
        extra_args=["--flush-session", "--dbs"],
    )
    command = build_sqlmap_command(config, Path("vendor/sqlmap/sqlmap.py"), tmp_path / "out")

    assert "-r" in command
    assert str(request_file) in command
    assert "--tamper" in command
    assert command[-2:] == ["--flush-session", "--dbs"]
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```powershell
python -m pytest tests/backend/test_command_builder.py -q
```

Expected: FAIL because `backend.sqlmap_gui.engine.command_builder` does not exist.

- [ ] **Step 3: Implement schemas and command builder**

Create `backend/sqlmap_gui/schemas/tasks.py` with `TaskStatus`, `ScanConfig`, `TaskRead`, `TaskEventRead`, and `ReportRead` Pydantic models. Create `backend/sqlmap_gui/engine/command_builder.py` with `build_sqlmap_command(config, sqlmap_script, output_dir)` that returns a list and never a shell string.

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```powershell
python -m pytest tests/backend/test_command_builder.py -q
```

Expected: `2 passed`.

- [ ] **Step 5: Commit command builder**

Run:

```powershell
git add backend/sqlmap_gui/core backend/sqlmap_gui/schemas backend/sqlmap_gui/engine tests/backend/test_command_builder.py
git commit -m "feat: add sqlmap command builder"
```

Expected: commit succeeds.

## Task 3: SQLite Repository and Artifacts

**Files:**
- Create: `backend/sqlmap_gui/db/database.py`
- Create: `backend/sqlmap_gui/db/repository.py`
- Create: `backend/sqlmap_gui/core/artifacts.py`
- Create: `tests/backend/test_repository.py`

- [ ] **Step 1: Write failing repository tests**

Create `tests/backend/test_repository.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```powershell
python -m pytest tests/backend/test_repository.py -q
```

Expected: FAIL because repository modules do not exist.

- [ ] **Step 3: Implement SQLite schema and repository**

Implement `init_database(db_path)` with tables `projects`, `targets`, `scan_templates`, `tasks`, `task_events`, and `reports`. Implement `Repository` methods used by tests and later API.

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```powershell
python -m pytest tests/backend/test_repository.py -q
```

Expected: `1 passed`.

- [ ] **Step 5: Commit data layer**

Run:

```powershell
git add backend/sqlmap_gui/db backend/sqlmap_gui/core/artifacts.py tests/backend/test_repository.py
git commit -m "feat: add sqlite task repository"
```

Expected: commit succeeds.

## Task 4: Task Manager, Engine, and Reports

**Files:**
- Create: `backend/sqlmap_gui/engine/subprocess_engine.py`
- Create: `backend/sqlmap_gui/tasks/events.py`
- Create: `backend/sqlmap_gui/tasks/manager.py`
- Create: `backend/sqlmap_gui/reports/service.py`
- Create: `tests/backend/test_task_manager.py`

- [ ] **Step 1: Write failing task manager test with fake engine**

Create `tests/backend/test_task_manager.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```powershell
python -m pytest tests/backend/test_task_manager.py -q
```

Expected: FAIL because task modules do not exist.

- [ ] **Step 3: Implement event hub, artifacts manager, report service, task manager, subprocess engine**

Implement `TaskManager.create_task`, `TaskManager.run_pending_once`, background worker support, cancellation, `EventHub.publish`, `SubprocessSqlmapEngine.run`, and `ReportService.create_basic_report`.

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```powershell
python -m pytest tests/backend/test_task_manager.py -q
```

Expected: `1 passed`.

- [ ] **Step 5: Commit task execution layer**

Run:

```powershell
git add backend/sqlmap_gui/engine/subprocess_engine.py backend/sqlmap_gui/tasks backend/sqlmap_gui/reports tests/backend/test_task_manager.py
git commit -m "feat: add task execution pipeline"
```

Expected: commit succeeds.

## Task 5: FastAPI Application

**Files:**
- Create: `backend/sqlmap_gui/api/app.py`
- Create: `backend/sqlmap_gui/api/routes.py`
- Modify: `backend/sqlmap_gui/main.py`
- Create: `tests/backend/test_api.py`

- [ ] **Step 1: Write failing API tests**

Create `tests/backend/test_api.py`:

```python
from pathlib import Path

from fastapi.testclient import TestClient

from backend.sqlmap_gui.api.app import create_app


def test_health_and_task_creation(tmp_path: Path):
    app = create_app(data_dir=tmp_path / "data", artifacts_dir=tmp_path / "artifacts", start_worker=False)
    client = TestClient(app)

    health = client.get("/api/health")
    created = client.post("/api/tasks", json={"target": "http://example.test/?id=1", "input_type": "url"})
    listed = client.get("/api/tasks")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert created.status_code == 200
    assert created.json()["status"] == "queued"
    assert listed.json()[0]["id"] == created.json()["id"]
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```powershell
python -m pytest tests/backend/test_api.py -q
```

Expected: FAIL because API app is missing.

- [ ] **Step 3: Implement FastAPI routes**

Implement `create_app(data_dir=None, artifacts_dir=None, start_worker=True)` with `/api/health`, `/api/tasks`, `/api/tasks/{id}`, `/api/tasks/{id}/logs`, `/api/tasks/{id}/report`, `/api/tasks/{id}/cancel`, and `/api/events`.

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```powershell
python -m pytest tests/backend/test_api.py -q
```

Expected: `1 passed`.

- [ ] **Step 5: Commit API layer**

Run:

```powershell
git add backend/sqlmap_gui/api backend/sqlmap_gui/main.py tests/backend/test_api.py
git commit -m "feat: expose fastapi task api"
```

Expected: commit succeeds.

## Task 6: Vendor sqlmap Sync

**Files:**
- Create: `vendor/sqlmap/**`
- Create: `scripts/sync-sqlmap.ps1`
- Modify: `.gitignore`

- [ ] **Step 1: Create sync script**

Create `scripts/sync-sqlmap.ps1` that copies from `C:\Users\31373\Downloads\sqlmap-master` into `vendor/sqlmap` while excluding `.git`, `__pycache__`, and `.pyc`.

- [ ] **Step 2: Run sync**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\sync-sqlmap.ps1
```

Expected: `vendor/sqlmap/sqlmap.py` exists.

- [ ] **Step 3: Verify sqlmap version source**

Run:

```powershell
python vendor\sqlmap\sqlmap.py --version
```

Expected: prints a sqlmap version from the synced source.

- [ ] **Step 4: Commit vendor sync**

Run:

```powershell
git add scripts/sync-sqlmap.ps1 vendor/sqlmap .gitignore
git commit -m "chore: vendor sqlmap master source"
```

Expected: commit succeeds.

## Task 7: React Workbench

**Files:**
- Create: `apps/web/index.html`
- Create: `apps/web/src/main.tsx`
- Create: `apps/web/src/App.tsx`
- Create: `apps/web/src/api.ts`
- Create: `apps/web/src/types.ts`
- Create: `apps/web/src/styles.css`

- [ ] **Step 1: Implement frontend DTOs and API client**

Create TypeScript types matching backend task DTOs. Implement `createTask`, `listTasks`, `getTaskLogs`, `getTaskReport`, and `subscribeEvents` in `apps/web/src/api.ts`.

- [ ] **Step 2: Implement professional workbench UI**

Implement a single-page Phase 1 workbench with project status, target/request input, preset selector, task list, command/log panel, and report summary panel.

- [ ] **Step 3: Typecheck frontend**

Run:

```powershell
npm run typecheck
```

Expected: no TypeScript errors after dependencies are installed.

- [ ] **Step 4: Commit web UI**

Run:

```powershell
git add apps/web
git commit -m "feat: add react workbench"
```

Expected: commit succeeds.

## Task 8: Electron Desktop and Dev Startup

**Files:**
- Create: `apps/desktop/main.cjs`
- Create: `scripts/start-dev.cjs`

- [ ] **Step 1: Implement Electron backend lifecycle**

Create `apps/desktop/main.cjs` that starts Python with `-m uvicorn backend.sqlmap_gui.main:app --host 127.0.0.1 --port 8765`, waits for `/api/health`, opens the React URL, and terminates Python when Electron quits.

- [ ] **Step 2: Implement dev launcher**

Create `scripts/start-dev.cjs` that starts Vite on `127.0.0.1:5173`, waits for it, then starts Electron with `VITE_DEV_SERVER_URL=http://127.0.0.1:5173`.

- [ ] **Step 3: Build web assets**

Run:

```powershell
npm run build:web
```

Expected: `apps/web/dist/index.html` exists.

- [ ] **Step 4: Commit desktop launcher**

Run:

```powershell
git add apps/desktop scripts/start-dev.cjs
git commit -m "feat: add electron desktop launcher"
```

Expected: commit succeeds.

## Task 9: Final Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README quick start**

Add a concise Phase 1 quick start:

```markdown
## Phase 1 Modern App

```powershell
python -m pip install -r requirements.txt
npm install
npm start
```
```

- [ ] **Step 2: Run backend and legacy tests**

Run:

```powershell
python -m pytest tests/backend tests/unit -q
```

Expected: all backend and legacy unit tests pass.

- [ ] **Step 3: Run frontend checks**

Run:

```powershell
npm run typecheck
npm run build:web
```

Expected: typecheck and build pass.

- [ ] **Step 4: Commit documentation and final verification**

Run:

```powershell
git add README.md
git commit -m "docs: document phase1 modern app startup"
```

Expected: commit succeeds.

