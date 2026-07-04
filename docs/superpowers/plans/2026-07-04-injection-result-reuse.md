# Injection Result Reuse Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist sqlmap injection results after task completion and make databases, tables, and columns visible and reusable in the UI.

**Architecture:** The backend remains the source of durable task results by auto-generating reports after completed scans. `ReportService` parses sqlmap logs into a normalized summary, `TaskManager` persists that summary without changing task status on report failures, and React consumes either report summaries or live-log fallback results. The UI keeps the existing `-D/-T/-C` inputs and result tags but makes completed-task results durable across refreshes and task switches.

**Tech Stack:** Python 3, FastAPI, SQLite repository, pytest, React 18, TypeScript, Vite.

---

## File Map

- Modify `backend/sqlmap_gui/reports/service.py`: strengthen log parsing and keep report summary fields stable.
- Modify `backend/sqlmap_gui/tasks/manager.py`: generate reports automatically after successful task completion and isolate report-generation errors.
- Modify `tests/backend/test_task_manager.py`: assert completed tasks create reports and report failures do not override task status.
- Create `tests/backend/test_report_service.py`: focused parser tests for databases/current DB/current user/tables/columns.
- Modify `apps/web/src/App.tsx`: make report-derived results authoritative, keep live-log fallback, show empty reusable-results state, and ensure result tags fill `custom_db/custom_table/custom_column`.

---

## Task 1: Add backend parser coverage

**Files:**
- Create: `tests/backend/test_report_service.py`
- Modify: none

- [ ] **Step 1: Write failing parser tests**

Create `tests/backend/test_report_service.py`:

```python
from pathlib import Path

from backend.sqlmap_gui.core.artifacts import ArtifactsManager
from backend.sqlmap_gui.reports.service import ReportService


def parse(lines: list[str], tmp_path: Path) -> dict[str, list[str]]:
    service = ReportService(ArtifactsManager(tmp_path / "artifacts"))
    return service._parse_injection_results(lines)


def test_parse_database_and_current_identity_results(tmp_path: Path):
    results = parse(
        [
            "[INFO] fetching database names",
            "available databases [2]",
            "[*] information_schema",
            "[*] security",
            "[INFO] fetched data logged to text files under output directory",
            "current database: 'security'",
            "current user: 'root@localhost'",
        ],
        tmp_path,
    )

    assert results["databases"] == ["information_schema", "security"]
    assert results["current_db"] == ["security"]
    assert results["current_user"] == ["root@localhost"]


def test_parse_table_and_column_ascii_sections(tmp_path: Path):
    results = parse(
        [
            "[INFO] fetching tables for database: 'security'",
            "+-------+",
            "| users |",
            "| emails |",
            "+-------+",
            "Database: security",
            "Table: users",
            "[3 columns]",
            "+----------+-------------+",
            "| Column   | Type        |",
            "+----------+-------------+",
            "| id       | int(11)     |",
            "| username | varchar(20) |",
            "| password | varchar(20) |",
            "+----------+-------------+",
        ],
        tmp_path,
    )

    assert results["tables"] == ["users", "emails"]
    assert results["columns"] == ["id", "username", "password"]
```

- [ ] **Step 2: Run parser tests and verify RED**

Run:

```powershell
python -m pytest tests/backend/test_report_service.py -q
```

Expected: FAIL because the new file does not exist before Step 1 or because the current parser misses at least the column/table scenario.

- [ ] **Step 3: Implement parser improvements**

Update `ReportService._parse_injection_results` so it:

- Detects database-list mode after `fetching database names` or `available databases`.
- Adds unique database names from `[*] name` lines only while in database mode.
- Detects table-list mode after `fetching tables for database`.
- Detects column-list mode after `Table:` and reads the first cell from sqlmap ASCII table rows.
- Ignores ASCII borders and header cells such as `Database`, `Column`, and `Type`.
- Keeps current database and current user parsing independent of the active phase.

- [ ] **Step 4: Run parser tests and verify GREEN**

Run:

```powershell
python -m pytest tests/backend/test_report_service.py -q
```

Expected: PASS.

---

## Task 2: Auto-generate report after completed task

**Files:**
- Modify: `backend/sqlmap_gui/tasks/manager.py`
- Modify: `tests/backend/test_task_manager.py`

- [ ] **Step 1: Add failing task-manager tests**

Append/update tests in `tests/backend/test_task_manager.py` so the fake engine emits database results and completed tasks are expected to have a report:

```python
class FakeEngine:
    def run(self, command, cwd, on_line, cancel_event):
        on_line("[INFO] testing target")
        on_line("[INFO] fetching database names")
        on_line("available databases [1]:")
        on_line("[*] security")
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
    assert report["summary_json"]
    assert '"security"' in report["summary_json"]
    assert hub.snapshot()[-1]["type"] == "status"
```

Also add:

```python
class ReportFailingTaskManager(TaskManager):
    def generate_report(self, task_id: str):
        raise RuntimeError("report parser failed")


def test_report_generation_failure_does_not_override_completed_task(tmp_path: Path):
    db_path = tmp_path / "app.sqlite3"
    init_database(db_path)
    repo = Repository(db_path)
    artifacts = ArtifactsManager(tmp_path / "artifacts")
    hub = EventHub()
    manager = ReportFailingTaskManager(repo, artifacts, FakeEngine(), hub, max_workers=1)
    project = repo.ensure_default_project()

    task = manager.create_task(project["id"], ScanConfig(target="http://example.test/?id=1"))
    manager.run_pending_once()

    stored = repo.get_task(task["id"])
    events = repo.list_task_events(task["id"])

    assert stored["status"] == "completed"
    assert any(event["type"] == "error" and "report parser failed" in event["message"] for event in events)
```

- [ ] **Step 2: Run task-manager tests and verify RED**

Run:

```powershell
python -m pytest tests/backend/test_task_manager.py -q
```

Expected: FAIL because completed tasks do not auto-create reports yet.

- [ ] **Step 3: Implement auto report generation**

Modify `TaskManager._run_task` after `finished = self.repo.finish_task(...)` and before publishing final status:

```python
if finished["status"] == TaskStatus.COMPLETED.value:
    try:
        self.generate_report(task_id)
    except Exception as report_exc:
        message = f"report generation failed: {report_exc}"
        self.artifacts.append_log(task_id, f"[ERROR] {message}")
        self.repo.add_task_event(task_id, "error", "error", message)
        self.hub.publish("error", task_id, message, level="error")
```

Do not change `finished` when report generation fails.

- [ ] **Step 4: Run task-manager tests and verify GREEN**

Run:

```powershell
python -m pytest tests/backend/test_task_manager.py -q
```

Expected: PASS.

---

## Task 3: Stabilize frontend result state and fallback behavior

**Files:**
- Modify: `apps/web/src/App.tsx`

- [ ] **Step 1: Add small result helpers**

Inside `App.tsx`, define a reusable empty result factory and report-summary conversion near `defaultConfig` or above `App`:

```tsx
type InjectionResults = Record<"databases" | "tables" | "columns" | "current_db" | "current_user", string[]>;

function emptyInjectionResults(): InjectionResults {
  return { databases: [], tables: [], columns: [], current_db: [], current_user: [] };
}

function resultsFromReport(report: ReportRead): InjectionResults {
  return {
    databases: report.summary.databases ?? [],
    tables: report.summary.tables ?? [],
    columns: report.summary.columns ?? [],
    current_db: report.summary.current_db ?? [],
    current_user: report.summary.current_user ?? [],
  };
}
```

- [ ] **Step 2: Replace duplicated inline result initialization**

Change `useState<Record<string, string[]>>({...})` to:

```tsx
const [injectionResults, setInjectionResults] = useState<InjectionResults>(() => emptyInjectionResults());
const [taskResultsCache, setTaskResultsCache] = useState<Map<string, InjectionResults>>(new Map());
```

Replace repeated manual result object construction with `emptyInjectionResults()` and `resultsFromReport(currentReport)`.

- [ ] **Step 3: Make report loading authoritative and log parsing fallback**

In the selected-task effect:

```tsx
useEffect(() => {
  if (!selectedTask) {
    setLogs([]);
    setReport(null);
    setInjectionResults(emptyInjectionResults());
    return;
  }

  getTaskLogs(selectedTask.id).then(setLogs).catch(() => {});
  getTaskReport(selectedTask.id).then((r) => {
    setReport(r);
    if (r?.summary) {
      const results = resultsFromReport(r);
      setInjectionResults(results);
      setTaskResultsCache((prev) => {
        const next = new Map(prev);
        next.set(selectedTask.id, results);
        return next;
      });
      return;
    }

    const cachedResults = taskResultsCache.get(selectedTask.id);
    setInjectionResults(cachedResults ?? emptyInjectionResults());
  }).catch(() => {
    const cachedResults = taskResultsCache.get(selectedTask.id);
    setInjectionResults(cachedResults ?? emptyInjectionResults());
  });
}, [selectedTask?.id]);
```

Keep the existing log parsing effect, but type it as returning `InjectionResults`.

- [ ] **Step 4: Keep result tags as one-click reuse controls**

Ensure existing click handlers remain:

```tsx
onClick={() => update("custom_db", db)}
onClick={() => update("custom_table", table)}
onClick={() => update("custom_column", column)}
```

If the columns group is absent, add it under the tables group:

```tsx
{injectionResults.columns.length > 0 && (
  <div className="result-group">
    <h3>列名列表</h3>
    <div className="result-tags">
      {injectionResults.columns.map((column, i) => (
        <span key={i} className="result-tag" onClick={() => update("custom_column", column)} title="点击使用此列名">
          {column}
        </span>
      ))}
    </div>
  </div>
)}
```

- [ ] **Step 5: Show completed-task empty state**

After the result card condition, add a muted card for completed tasks with no parsed result:

```tsx
{selectedTask && selectedTask.status === "completed" && !Object.values(injectionResults).some((arr) => arr.length > 0) && (
  <div className="card results-card">
    <h2>注入结果</h2>
    <p className="muted">暂无可复用结果，可尝试执行 --dbs、--tables、--columns 或导出结果生成结构化报告。</p>
  </div>
)}
```

- [ ] **Step 6: Run TypeScript check**

Run:

```powershell
npm run typecheck
```

Expected: PASS.

---

## Task 4: Full verification

**Files:**
- Test-only verification across backend and frontend.

- [ ] **Step 1: Run backend tests**

Run:

```powershell
python -m pytest tests/backend -q
```

Expected: PASS.

- [ ] **Step 2: Run frontend typecheck**

Run:

```powershell
npm run typecheck
```

Expected: PASS.

- [ ] **Step 3: Run frontend build**

Run:

```powershell
npm run build:web
```

Expected: PASS.

- [ ] **Step 4: Review diff**

Run:

```powershell
git diff -- backend/sqlmap_gui/reports/service.py backend/sqlmap_gui/tasks/manager.py tests/backend/test_report_service.py tests/backend/test_task_manager.py apps/web/src/App.tsx docs/superpowers/plans/2026-07-04-injection-result-reuse.md
```

Expected: Diff only includes parser tests, auto report generation, frontend result-state cleanup, and this plan.
