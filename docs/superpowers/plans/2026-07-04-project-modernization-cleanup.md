# Project Modernization Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 收敛项目到现代 Electron + React + FastAPI 主线，保留有效功能改动，删除旧架构和运行产物。

**Architecture:** 保留 `apps/`、`backend/`、`vendor/sqlmap/`、现代测试和启动脚本。删除旧 `GUI-CN/`、`framework/`、`config/`、根目录 `sqlmap/`、运行数据库、扫描产物、调试截图和缓存。通过 `.gitignore` 防止无关文件回流，并用后端测试、TypeScript 检查和 Web 构建验证。

**Tech Stack:** Electron, React, TypeScript, Vite, FastAPI, SQLite, pytest, sqlmap vendor source.

---

## File Map

- Modify: `.gitignore` — ignore runtime artifacts, sqlite files, screenshots, local tool caches, build outputs.
- Modify: `package.json` — remove stale `test:legacy` command and keep modern scripts.
- Modify: `README.md` — replace legacy mojibake-heavy instructions with concise modern project instructions.
- Keep/Add: `start.bat`, `start.sh` — modern startup helpers.
- Delete: `启动.bat` — duplicate mojibake launcher.
- Delete: `GUI-CN/`, `framework/`, `config/`, `sqlmap/` — old architecture and duplicate sqlmap root copy.
- Delete: `artifacts/test-run*/`, `artifacts/tasks/`, `data/*.sqlite3*`, `.pytest_cache/`, `.playwright-mcp/`, `scroll-*.png` — generated/local files.
- Keep: `vendor/sqlmap/` — backend runtime dependency.
- Keep: `tests/backend/`, `tests/frontend/` — modern tests.

---

## Task 1: Protect modern scripts and ignore generated files

**Files:**
- Modify: `.gitignore`
- Modify: `package.json`
- Add: `start.bat`
- Add: `start.sh`
- Delete: `启动.bat`

- [ ] **Step 1: Update `.gitignore`**

Ensure `.gitignore` contains these entries:

```gitignore
# Python
__pycache__/
*.py[cod]
*.pyo
.pytest_cache/

# Node / frontend
node_modules/
dist/
apps/web/dist/

# Runtime data
artifacts/
data/*.sqlite3
data/*.sqlite3-shm
data/*.sqlite3-wal
*.log

# Local tooling
.playwright-mcp/
.omo/
.claude/
.superpowers/
.tmp/

# Debug screenshots / OS files
scroll-*.png
.DS_Store
Thumbs.db
```

- [ ] **Step 2: Update `package.json` scripts**

Change scripts to:

```json
"scripts": {
  "start": "node scripts/start-dev.cjs",
  "build:web": "vite build apps/web",
  "typecheck": "tsc --noEmit",
  "test:backend": "python -m pytest tests/backend -q"
}
```

Remove `test:legacy` because `tests/unit/` belongs to the old deleted framework.

- [ ] **Step 3: Keep modern launchers**

Keep `start.bat` and `start.sh` because both call `npm start` for the modern app.

- [ ] **Step 4: Delete duplicate mojibake launcher**

Delete `启动.bat` because it duplicates `start.bat` and contains mojibake text.

---

## Task 2: Rewrite README for modern project state

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace README with concise modern instructions**

Use this structure:

```markdown
# SQLmap GUI 2.0

Modern desktop GUI for sqlmap built with Electron, React, and FastAPI.

## Architecture

- `apps/desktop/` — Electron shell.
- `apps/web/` — React + Vite workbench.
- `backend/sqlmap_gui/` — FastAPI backend, task queue, SQLite repository, report generation.
- `vendor/sqlmap/` — bundled sqlmap source used by the backend.
- `artifacts/` and `data/` — runtime output directories, ignored by git.

## Requirements

- Python 3.11+
- Node.js 20+

## Setup

```powershell
python -m pip install -r requirements.txt
npm install
```

## Start

```powershell
npm start
```

Windows users can also run:

```powershell
.\start.bat
```

Linux/macOS users can run:

```bash
./start.sh
```

## Verification

```powershell
python -m pytest tests/backend -q
npm run typecheck
npm run build:web
```

## Runtime Data

Scan logs, reports, sqlite databases, and sqlmap output are generated under `artifacts/` and `data/`; they are local runtime files and are not committed.
```

---

## Task 3: Remove old architecture and generated files safely

**Files/directories:**
- Delete: `GUI-CN/`
- Delete: `framework/`
- Delete: `config/`
- Delete: `sqlmap/`
- Delete: `tests/unit/`
- Delete: `artifacts/test-run/`
- Delete: `artifacts/test-run-2/`
- Delete: `artifacts/tasks/`
- Delete: `.pytest_cache/`
- Delete: `.playwright-mcp/`
- Delete: `scroll-bottom.png`
- Delete: `scroll-top-final.png`
- Delete: `data/sqlmap-gui.sqlite3`, `data/sqlmap-gui.sqlite3-shm`, `data/sqlmap-gui.sqlite3-wal`

- [ ] **Step 1: Verify delete targets are inside repo**

Run a PowerShell script that resolves each target and checks it starts with the repository root path before deletion.

- [ ] **Step 2: Delete targets**

Use PowerShell `Remove-Item -LiteralPath ... -Recurse -Force` only after Step 1 passes.

- [ ] **Step 3: Confirm `vendor/sqlmap/sqlmap.py` remains**

Run:

```powershell
Test-Path vendor\sqlmap\sqlmap.py
```

Expected: `True`.

---

## Task 4: Verify modern app after cleanup

**Files:**
- No direct edits unless verification exposes a modern-app regression.

- [ ] **Step 1: Run backend tests**

```powershell
python -m pytest tests/backend -q
```

Expected: all backend tests pass.

- [ ] **Step 2: Run TypeScript check**

```powershell
npm run typecheck
```

Expected: `tsc --noEmit` exits 0.

- [ ] **Step 3: Run web build**

```powershell
npm run build:web
```

Expected: Vite build exits 0.

- [ ] **Step 4: Review status**

```powershell
git status --short
```

Expected: only intentional modern source/doc/test/start-script changes and intentional deletions remain.

---

## Task 5: Commit modernization cleanup

**Files:**
- Stage all intended changes from Tasks 1-4.

- [ ] **Step 1: Stage intended changes**

Stage:

```text
.gitignore
package.json
README.md
start.bat
start.sh
apps/web/src/App.tsx
apps/web/src/api.ts
apps/web/src/styles.css
apps/web/src/types.ts
backend/sqlmap_gui/**
tests/backend/**
tests/frontend/**
docs/superpowers/**
```

Also stage deletions for old architecture and generated tracked files:

```text
GUI-CN/
framework/
config/
sqlmap/
tests/unit/
artifacts/test-run/
artifacts/test-run-2/
.claude/settings.local.json
```

Do not stage ignored runtime files such as `artifacts/tasks/`, `data/*.sqlite3*`, `.pytest_cache/`, `.playwright-mcp/`, `node_modules/`, or `apps/web/dist/`.

- [ ] **Step 2: Commit**

```powershell
git commit -m "chore: modernize project layout and cleanup artifacts"
```

- [ ] **Step 3: Final status**

```powershell
git status --short
```

Expected: no source changes from this work remain; ignored local runtime directories may still exist but should not appear.
