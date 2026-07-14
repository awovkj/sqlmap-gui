# SQLmap GUI 2.0

Modern desktop GUI for sqlmap built with Electron, React, and FastAPI.

## Architecture

- `apps/desktop/` — Electron shell that boots the backend and loads the workbench.
- `apps/web/` — React + Vite workbench.
  - `src/lib/` — pure helpers (injection-log parsing, command preview, status mapping).
  - `src/components/` — reusable UI pieces; `src/constants.ts` / `src/config.ts` hold option catalogs and defaults.
- `backend/sqlmap_gui/` — FastAPI backend, concurrent task queue, SQLite repository, report generation.
- `vendor/sqlmap/` — bundled sqlmap source used by the backend.
- `artifacts/` and `data/` — runtime output directories, ignored by git.

The backend runs queued scans concurrently via a worker pool (`TaskManager`, default 2 workers). Cancelling or timing out a scan terminates the whole sqlmap process tree. SQLite access uses per-thread WAL connections; injection results are parsed authoritatively on the backend, with the frontend parser acting as a live/fallback preview.

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

To start from Explorer without leaving a command prompt visible, double-click:

```text
SQLmap GUI.vbs
```

Linux/macOS users can run:

```bash
./start.sh
```

## Verification

```powershell
python -m pytest -q
npm run typecheck
npm run build:web
```

Optional Python lint (dev tool, not a runtime dependency):

```powershell
python -m pip install ruff
ruff check backend tests
```

## Runtime Data

Scan logs, reports, sqlite databases, and sqlmap output are generated under `artifacts/` and `data/`; they are local runtime files and are not committed.
