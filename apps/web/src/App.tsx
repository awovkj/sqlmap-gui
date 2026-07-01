import { FormEvent, useEffect, useMemo, useState } from "react";

import { createTask, getTaskLogs, getTaskReport, health, listTasks, subscribeEvents } from "./api";
import type { InputType, Preset, ReportRead, TaskEvent, TaskRead } from "./types";

const PRESETS: Array<{ value: Preset; label: string; description: string }> = [
  { value: "balanced", label: "平衡测试", description: "level 3 / risk 2 / threads 6" },
  { value: "deep", label: "深度测试", description: "level 5 / risk 3 / threads 10" },
  { value: "waf", label: "WAF 绕过", description: "text-only + tamper 组合" },
];

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    queued: "排队中",
    running: "运行中",
    completed: "已完成",
    failed: "失败",
    cancelling: "取消中",
    cancelled: "已取消",
    interrupted: "已中断",
  };
  return labels[status] ?? status;
}

export default function App() {
  const [target, setTarget] = useState("http://127.0.0.1/vuln.php?id=1");
  const [inputType, setInputType] = useState<InputType>("url");
  const [preset, setPreset] = useState<Preset>("balanced");
  const [extraArgs, setExtraArgs] = useState("");
  const [tasks, setTasks] = useState<TaskRead[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [logs, setLogs] = useState<TaskEvent[]>([]);
  const [report, setReport] = useState<ReportRead | null>(null);
  const [backendStatus, setBackendStatus] = useState("连接中");
  const [error, setError] = useState<string | null>(null);
  const selectedTask = useMemo(
    () => tasks.find((task) => task.id === selectedTaskId) ?? tasks[0] ?? null,
    [selectedTaskId, tasks],
  );

  async function refreshTasks() {
    const next = await listTasks();
    setTasks(next);
    if (!selectedTaskId && next.length > 0) {
      setSelectedTaskId(next[0].id);
    }
  }

  useEffect(() => {
    health()
      .then(() => setBackendStatus("后端在线"))
      .catch((failure: Error) => {
        setBackendStatus("后端离线");
        setError(failure.message);
      });
    refreshTasks().catch((failure: Error) => setError(failure.message));
    const events = subscribeEvents(
      (event) => {
        if (event.type === "log") {
          setLogs((current) => [...current.slice(-300), event]);
        }
        if (event.type === "status") {
          refreshTasks().catch((failure: Error) => setError(failure.message));
        }
      },
      () => setBackendStatus("事件流重连中"),
    );
    return () => events.close();
  }, []);

  useEffect(() => {
    if (!selectedTask) {
      setLogs([]);
      setReport(null);
      return;
    }
    getTaskLogs(selectedTask.id)
      .then(setLogs)
      .catch((failure: Error) => setError(failure.message));
    getTaskReport(selectedTask.id)
      .then(setReport)
      .catch((failure: Error) => setError(failure.message));
  }, [selectedTask?.id]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    const task = await createTask({
      target,
      input_type: inputType,
      preset,
      extra_args: extraArgs.split(/\s+/).map((item) => item.trim()).filter(Boolean),
    });
    setSelectedTaskId(task.id);
    await refreshTasks();
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">SQLmap GUI 2.0 · Phase 1</p>
          <h1>专业扫描工作台</h1>
        </div>
        <div className="status-pill">{backendStatus}</div>
      </header>

      {error ? <section className="error-card">{error}</section> : null}

      <section className="workspace-grid">
        <aside className="sidebar card">
          <h2>资源</h2>
          <button className="nav-item active">Default 项目</button>
          <button className="nav-item">目标资产</button>
          <button className="nav-item">请求包库</button>
          <button className="nav-item">历史任务</button>
          <div className="metric-card">
            <span>任务总数</span>
            <strong>{tasks.length}</strong>
          </div>
        </aside>

        <section className="card scan-card">
          <div className="card-header">
            <div>
              <p className="eyebrow">New Scan</p>
              <h2>创建扫描任务</h2>
            </div>
            <button className="ghost-button" onClick={() => refreshTasks().catch((failure: Error) => setError(failure.message))}>
              刷新任务
            </button>
          </div>

          <form onSubmit={(event) => submit(event).catch((failure: Error) => setError(failure.message))}>
            <label className="field-label">输入类型</label>
            <div className="segmented">
              <button type="button" className={inputType === "url" ? "selected" : ""} onClick={() => setInputType("url")}>
                单 URL
              </button>
              <button
                type="button"
                className={inputType === "raw_request" ? "selected" : ""}
                onClick={() => setInputType("raw_request")}
              >
                原始请求
              </button>
            </div>

            <label className="field-label">目标 / 请求包</label>
            <textarea value={target} onChange={(event) => setTarget(event.target.value)} rows={9} />

            <label className="field-label">扫描预设</label>
            <div className="preset-grid">
              {PRESETS.map((item) => (
                <button
                  key={item.value}
                  type="button"
                  className={preset === item.value ? "preset selected" : "preset"}
                  onClick={() => setPreset(item.value)}
                >
                  <strong>{item.label}</strong>
                  <span>{item.description}</span>
                </button>
              ))}
            </div>

            <label className="field-label">高级参数（原样追加）</label>
            <input value={extraArgs} onChange={(event) => setExtraArgs(event.target.value)} placeholder="例如 --dbs --flush-session" />

            <button className="primary-button" type="submit">启动任务</button>
          </form>
        </section>

        <aside className="right-panel">
          <section className="card">
            <div className="card-header">
              <h2>任务队列</h2>
            </div>
            <div className="task-list">
              {tasks.map((task) => (
                <button
                  key={task.id}
                  className={selectedTask?.id === task.id ? "task-item selected" : "task-item"}
                  onClick={() => setSelectedTaskId(task.id)}
                >
                  <span>{statusLabel(task.status)}</span>
                  <strong>{task.target}</strong>
                  <small>{task.id}</small>
                </button>
              ))}
              {tasks.length === 0 ? <p className="muted">暂无任务</p> : null}
            </div>
          </section>

          <section className="card terminal-card">
            <div className="card-header">
              <h2>实时日志</h2>
            </div>
            <pre>{logs.map((line) => line.message).join("\n") || "等待任务输出..."}</pre>
          </section>
        </aside>
      </section>

      <section className="bottom-grid">
        <section className="card">
          <h2>命令预览</h2>
          <pre>{selectedTask ? selectedTask.command.join(" ") || "任务排队后生成命令" : "选择任务查看命令"}</pre>
        </section>
        <section className="card">
          <h2>报告摘要</h2>
          {report ? (
            <dl className="report-list">
              <dt>状态</dt><dd>{report.summary.status}</dd>
              <dt>日志行</dt><dd>{report.summary.log_lines}</dd>
              <dt>JSON</dt><dd>{report.json_path}</dd>
            </dl>
          ) : (
            <p className="muted">任务完成后生成报告。</p>
          )}
        </section>
      </section>
    </main>
  );
}
