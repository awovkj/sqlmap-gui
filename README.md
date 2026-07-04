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
