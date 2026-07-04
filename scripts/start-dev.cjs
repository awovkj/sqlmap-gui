const { spawn } = require("node:child_process");
const path = require("node:path");

const repoRoot = path.resolve(__dirname, "..");
const viteUrl = "http://127.0.0.1:5173";
const isWindows = process.platform === "win32";
const npmCommand = isWindows ? "npm.cmd" : "npm";
const electronBin = path.join(
  repoRoot,
  "node_modules",
  ".bin",
  isWindows ? "electron.cmd" : "electron",
);

const children = [];

function spawnChild(command, args, env = {}) {
  const child = spawn(command, args, {
    cwd: repoRoot,
    env: { ...process.env, ...env },
    stdio: "inherit",
    shell: isWindows,
    windowsHide: isWindows,
  });
  children.push(child);
  child.on("exit", (code) => {
    if (code && code !== 0) {
      console.error(`${command} exited with code ${code}`);
    }
  });
  return child;
}

async function waitForUrl(url, timeoutMs = 30000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        return;
      }
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
  }
  throw new Error(`Timed out waiting for ${url}`);
}

function stopChildren() {
  for (const child of children) {
    if (!child.killed) {
      child.kill();
    }
  }
}

process.on("SIGINT", () => {
  stopChildren();
  process.exit(130);
});
process.on("SIGTERM", () => {
  stopChildren();
  process.exit(143);
});
process.on("exit", stopChildren);

async function main() {
  spawnChild(npmCommand, ["exec", "vite", "--", "apps/web", "--host", "127.0.0.1", "--port", "5173"]);
  await waitForUrl(viteUrl);
  const electron = spawnChild(electronBin, ["apps/desktop/main.cjs"], {
    VITE_DEV_SERVER_URL: viteUrl,
    VITE_API_BASE: "http://127.0.0.1:8765/api",
  });
  electron.on("exit", (code) => {
    stopChildren();
    process.exit(code ?? 0);
  });
}

main().catch((error) => {
  console.error(error);
  stopChildren();
  process.exit(1);
});
