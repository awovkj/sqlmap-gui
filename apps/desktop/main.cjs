const { app, BrowserWindow } = require("electron");
const { spawn } = require("node:child_process");
const path = require("node:path");

const REPO_ROOT = path.resolve(__dirname, "..", "..");
const BACKEND_HOST = "127.0.0.1";
const BACKEND_PORT = process.env.SQLMAP_GUI_BACKEND_PORT || "8765";
const BACKEND_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}`;

let backendProcess = null;
let mainWindow = null;
const backendLogs = [];

function appendBackendLog(chunk) {
  const text = chunk.toString();
  backendLogs.push(text);
  if (backendLogs.length > 200) {
    backendLogs.splice(0, backendLogs.length - 200);
  }
}

function startBackend() {
  if (backendProcess) {
    return;
  }
  backendProcess = spawn(
    process.env.SQLMAP_GUI_PYTHON || "python",
    ["-m", "uvicorn", "backend.sqlmap_gui.main:app", "--host", BACKEND_HOST, "--port", BACKEND_PORT],
    {
      cwd: REPO_ROOT,
      env: {
        ...process.env,
        PYTHONIOENCODING: "utf-8",
        PYTHONUTF8: "1",
        PYTHONUNBUFFERED: "1",
      },
      windowsHide: true,
    },
  );
  backendProcess.stdout.on("data", appendBackendLog);
  backendProcess.stderr.on("data", appendBackendLog);
  backendProcess.on("exit", (code) => appendBackendLog(`\n[backend exited] ${code}\n`));
}

async function waitForBackend(timeoutMs = 15000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    try {
      const response = await fetch(`${BACKEND_URL}/api/health`);
      if (response.ok) {
        return;
      }
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 400));
    }
  }
  throw new Error(`Backend did not become healthy within ${timeoutMs}ms`);
}

function diagnosticHtml(error) {
  return `<!doctype html>
  <meta charset="utf-8">
  <title>SQLmap GUI Backend Diagnostics</title>
  <style>
    body { font-family: "Segoe UI", sans-serif; padding: 28px; background: #0f172a; color: #e2e8f0; }
    pre { white-space: pre-wrap; background: #020617; padding: 18px; border-radius: 14px; }
  </style>
  <h1>后端启动失败</h1>
  <p>${String(error).replace(/[<>&]/g, (c) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;" })[c])}</p>
  <h2>启动日志</h2>
  <pre>${backendLogs.join("").replace(/[<>&]/g, (c) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;" })[c])}</pre>`;
}

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 940,
    minWidth: 1100,
    minHeight: 760,
    title: "SQLmap GUI",
    backgroundColor: "#eef4ff",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  startBackend();
  try {
    await waitForBackend();
    const devUrl = process.env.VITE_DEV_SERVER_URL;
    if (devUrl) {
      await mainWindow.loadURL(devUrl);
    } else {
      await mainWindow.loadFile(path.join(REPO_ROOT, "apps", "web", "dist", "index.html"));
    }
  } catch (error) {
    await mainWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(diagnosticHtml(error))}`);
  }
}

app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", () => {
  if (backendProcess && !backendProcess.killed) {
    backendProcess.kill();
  }
});
