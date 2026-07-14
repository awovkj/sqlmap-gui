import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { cancelTask, clearAllTasks, createTask, downloadReport, generateTaskReport, getTaskLogs, getTaskReport, health, listTasks, subscribeEvents } from "./api";
import {
  DBMS_OPTIONS,
  INPUT_TYPE_BUTTONS,
  MAX_RENDERED_LOG_LINES,
  PARAM_FILTER_OPTIONS,
  PRESETS,
  REQUEST_EXAMPLE,
  TAMPER_PRESETS,
  TECHNIQUES,
  URL_EXAMPLE,
} from "./constants";
import { defaultConfig } from "./config";
import { Section } from "./components/Section";
import { SelectOrInput } from "./components/SelectOrInput";
import {
  InjectionResults,
  emptyInjectionResults,
  parseInjectionResults,
  resultsFromReport,
} from "./lib/injection";
import { buildPreviewCommand } from "./lib/command";
import { statusClass, statusLabel } from "./lib/status";
import type { Preset, ReportRead, ScanConfig, TaskEvent, TaskRead } from "./types";

/* ── App ────────────────────────────────────────────────── */

export default function App() {
  const [cfg, setCfg] = useState<ScanConfig>(defaultConfig);
  const [tasks, setTasks] = useState<TaskRead[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [logs, setLogs] = useState<TaskEvent[]>([]);
  const [report, setReport] = useState<ReportRead | null>(null);
  const [backendStatus, setBackendStatus] = useState("连接中");
  const [error, setError] = useState<string | null>(null);
  const [cancellingTaskId, setCancellingTaskId] = useState<string | null>(null);
  const [injectionResults, setInjectionResults] = useState<InjectionResults>(() => emptyInjectionResults());
  const [taskResultsCache, setTaskResultsCache] = useState<Map<string, InjectionResults>>(new Map());
  const [autoScroll, setAutoScroll] = useState(true);
  const logEndRef = useRef<HTMLDivElement>(null);
  const logScrollRef = useRef<HTMLDivElement>(null);

  const selectedTask = useMemo(
    () => tasks.find((t) => t.id === selectedTaskId) ?? tasks[0] ?? null,
    [selectedTaskId, tasks],
  );

  const previewCommand = useMemo(() => buildPreviewCommand(cfg), [cfg]);

  const visibleLogs = useMemo(
    () => (logs.length > MAX_RENDERED_LOG_LINES ? logs.slice(-MAX_RENDERED_LOG_LINES) : logs),
    [logs],
  );

  const update = useCallback(<K extends keyof ScanConfig>(key: K, val: ScanConfig[K]) => {
    setCfg((prev) => ({ ...prev, [key]: val }));
  }, []);

  /* ── Effects ─────────────────────────────────────────── */

  async function refreshTasks() {
    const next = await listTasks();
    setTasks(next);
    if (!selectedTaskId && next.length > 0) setSelectedTaskId(next[0].id);
  }

  useEffect(() => {
    health()
      .then(() => setBackendStatus("后端在线"))
      .catch((err: Error) => { setBackendStatus("后端离线"); setError(err.message); });
    refreshTasks().catch((err: Error) => setError(err.message));
    const events = subscribeEvents(
      (event) => {
        if (event.type === "log") setLogs((cur) => [...cur, event]);
        if (event.type === "status") refreshTasks().catch(() => {});
      },
      () => setBackendStatus("事件流重连中"),
    );
    return () => events.close();
  }, []);

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

  useEffect(() => {
    if (autoScroll) {
      logEndRef.current?.scrollIntoView({ behavior: "auto" });
    }
  }, [logs, autoScroll]);

  useEffect(() => {
    if (logs.length > 0 && selectedTask && !report) {
      const results = parseInjectionResults(logs);
      setInjectionResults(results);
      setTaskResultsCache((prev) => {
        const next = new Map(prev);
        next.set(selectedTask.id, results);
        return next;
      });
    }
  }, [logs, selectedTask?.id, report]);

  /* ── Handlers ────────────────────────────────────────── */

  function handleLogScroll() {
    const el = logScrollRef.current;
    if (!el) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 48;
    setAutoScroll(nearBottom);
  }

  function applyPreset(preset: Preset) {
    update("preset", preset);
    const base = { level: 3, risk: 2, threads: 6, batch: true, random_agent: true };
    switch (preset) {
      case "balanced":
        setCfg((p) => ({ ...p, ...base, text_only: false, skip_waf: false, tamper: [], tamper_preset: "通用绕过" }));
        break;
      case "deep":
        setCfg((p) => ({ ...p, level: 5, risk: 3, threads: 10, batch: true, random_agent: true, text_only: false, skip_waf: false, tamper: [], tamper_preset: "通用绕过" }));
        break;
      case "waf":
        setCfg((p) => ({
          ...p, level: 4, risk: 2, threads: 4, batch: true, random_agent: true,
          text_only: true, skip_waf: true, force_ssl: true,
          tamper: TAMPER_PRESETS["WAF 强化"], tamper_preset: "WAF 强化",
        }));
        break;
      case "enum_structure":
        setCfg((p) => ({ ...p, ...base, text_only: false, skip_waf: false, tamper: [], tamper_preset: "通用绕过", dbs: true, tables: true }));
        break;
      case "data_export":
        setCfg((p) => ({ ...p, ...base, text_only: false, skip_waf: false, tamper: [], tamper_preset: "通用绕过", dump_all: true }));
        break;
    }
  }

  function applyTamperPreset(name: string) {
    update("tamper_preset", name);
    update("tamper", TAMPER_PRESETS[name] ?? []);
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!cfg.target.trim() && cfg.input_type === "url") {
      setError("请输入目标 URL");
      return;
    }
    try {
      const task = await createTask(cfg);
      setSelectedTaskId(task.id);
      await refreshTasks();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleCancelTask(taskId: string) {
    setCancellingTaskId(taskId);
    try {
      await cancelTask(taskId);
      await refreshTasks();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setCancellingTaskId(null);
    }
  }

  async function handleExportReport(format: "json" | "html" | "markdown") {
    if (!selectedTask) return;
    try {
      const currentReport = report ?? await generateTaskReport(selectedTask.id);
      setReport(currentReport);
      if (currentReport?.summary) {
        const results = resultsFromReport(currentReport);
        setInjectionResults(results);
        setTaskResultsCache((prev) => {
          const next = new Map(prev);
          next.set(selectedTask.id, results);
          return next;
        });
      }
      downloadReport(selectedTask.id, format);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleClearAllTasks() {
    if (!confirm("确定要清空所有任务吗？")) return;
    try {
      await clearAllTasks();
      setTasks([]);
      setSelectedTaskId(null);
      setLogs([]);
      setReport(null);
      setInjectionResults(emptyInjectionResults());
      setTaskResultsCache(new Map());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  /* ── Render ──────────────────────────────────────────── */

  return (
    <main className="app-shell">
      {/* ── Topbar ── */}
      <header className="topbar">
        <div className="topbar-left">
          <h1 className="topbar-title">SQLmap GUI 2.0</h1>
          <span className="topbar-version">Phase 1</span>
        </div>
        <div className="topbar-center">
          <label className="topbar-label">预设</label>
          <select
            className="topbar-select"
            value={cfg.preset}
            onChange={(e) => applyPreset(e.target.value as Preset)}
          >
            {PRESETS.map((p) => (
              <option key={p.value} value={p.value}>{p.label} — {p.description}</option>
            ))}
          </select>
        </div>
        <div className="topbar-right">
          <span className={`status-pill ${backendStatus === "后端在线" ? "online" : "offline"}`}>
            {backendStatus}
          </span>
        </div>
      </header>

      {error && <div className="error-bar">{error}<button onClick={() => setError(null)}>×</button></div>}

      {/* ── 3-Column Layout ── */}
      <div className="workspace">

        {/* ── LEFT: Parameters ── */}
        <aside className="left-panel">
          <div className="left-panel-card">
            <div className="left-panel-card-header">
              <h2>参数配置</h2>
              <span>滚动查看全部选项</span>
            </div>
            <div className="left-panel-scroll" aria-label="SQLmap 参数配置">
              <Section title="扫描配置">
                <div className="field-row">
                  <label>Level</label>
                  <select value={cfg.level ?? 1} onChange={(e) => update("level", Number(e.target.value))}>
                    {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}
                  </select>
                </div>
                <div className="field-row">
                  <label>Risk</label>
                  <select value={cfg.risk ?? 1} onChange={(e) => update("risk", Number(e.target.value))}>
                    {[1, 2, 3].map((n) => <option key={n} value={n}>{n}</option>)}
                  </select>
                </div>
                <div className="field-row">
                  <label>线程</label>
                  <input type="number" min={1} max={20} value={cfg.threads ?? 10}
                    onChange={(e) => update("threads", Number(e.target.value) || 10)} />
                </div>
                <div className="field-row">
                  <label>批量并发</label>
                  <input type="number" min={1} max={20} value={cfg.batch_workers ?? 5}
                    onChange={(e) => update("batch_workers", Number(e.target.value) || 5)} />
                </div>
                <div className="field-row">
                  <label>技术</label>
                  <select value={cfg.technique ?? "BESUTQ"}
                    onChange={(e) => update("technique", e.target.value)}>
                    {TECHNIQUES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </select>
                </div>
                <div className="field-row">
                  <label>DBMS</label>
                  <select value={cfg.dbms ?? ""} onChange={(e) => update("dbms", e.target.value || undefined)}>
                    {DBMS_OPTIONS.map((d) => <option key={d} value={d}>{d || "自动检测"}</option>)}
                  </select>
                </div>
              </Section>

          <Section title="目标范围">
            <div className="field-row">
              <label>-p 指定参数</label>
              <input value={cfg.test_parameter ?? ""} onChange={(e) => update("test_parameter", e.target.value || undefined)} placeholder="如 id" />
            </div>
            <div className="field-row">
              <label>-D 数据库</label>
              <SelectOrInput
                value={cfg.custom_db ?? ""}
                onChange={(val) => update("custom_db", val || undefined)}
                options={injectionResults.databases ?? []}
                placeholder="输入或选择数据库"
              />
            </div>
            <div className="field-row">
              <label>-T 表名</label>
              <SelectOrInput
                value={cfg.custom_table ?? ""}
                onChange={(val) => update("custom_table", val || undefined)}
                options={injectionResults.tables ?? []}
                placeholder="输入或选择表名"
              />
            </div>
            <div className="field-row">
              <label>-C 列名</label>
              <SelectOrInput
                value={cfg.custom_column ?? ""}
                onChange={(val) => update("custom_column", val || undefined)}
                options={injectionResults.columns ?? []}
                placeholder="输入或选择列名"
              />
            </div>
            <div className="field-row">
              <label>参数过滤</label>
              <select value={cfg.param_filter ?? ""} onChange={(e) => update("param_filter", e.target.value || undefined)}>
                {PARAM_FILTER_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
          </Section>

          <Section title="注入控制">
            <div className="field-row">
              <label>跳过参数</label>
              <input value={cfg.skip_parameter ?? ""} onChange={(e) => update("skip_parameter", e.target.value || undefined)} />
            </div>
            <div className="field-row">
              <label>参数排除</label>
              <input value={cfg.param_exclude ?? ""} onChange={(e) => update("param_exclude", e.target.value || undefined)} />
            </div>
            <div className="field-row">
              <label>前缀</label>
              <input value={cfg.prefix ?? ""} onChange={(e) => update("prefix", e.target.value || undefined)} />
            </div>
            <div className="field-row">
              <label>后缀</label>
              <input value={cfg.suffix ?? ""} onChange={(e) => update("suffix", e.target.value || undefined)} />
            </div>
            <div className="field-row">
              <label>超时秒数</label>
              <input type="number" min={1} value={cfg.time_sec ?? ""}
                onChange={(e) => update("time_sec", e.target.value ? Number(e.target.value) : undefined)} />
            </div>
            <div className="field-row">
              <label>联合列数</label>
              <input value={cfg.union_cols ?? ""} onChange={(e) => update("union_cols", e.target.value || undefined)} placeholder="如 1-10" />
            </div>
            <div className="field-row">
              <label>联合字符</label>
              <input value={cfg.union_char ?? ""} onChange={(e) => update("union_char", e.target.value || undefined)} />
            </div>
            <div className="field-row">
              <label>联合来源</label>
              <input value={cfg.union_from ?? ""} onChange={(e) => update("union_from", e.target.value || undefined)} />
            </div>
            <div className="field-row">
              <label>联合值</label>
              <input value={cfg.union_values ?? ""} onChange={(e) => update("union_values", e.target.value || undefined)} />
            </div>
          </Section>

          <Section title="检测控制">
            <div className="field-row">
              <label>匹配字符串</label>
              <input value={cfg.string ?? ""} onChange={(e) => update("string", e.target.value || undefined)} />
            </div>
            <div className="field-row">
              <label>排除字符串</label>
              <input value={cfg.not_string ?? ""} onChange={(e) => update("not_string", e.target.value || undefined)} />
            </div>
            <div className="field-row">
              <label>正则表达式</label>
              <input value={cfg.regexp ?? ""} onChange={(e) => update("regexp", e.target.value || undefined)} />
            </div>
            <div className="field-row">
              <label>HTTP 代码</label>
              <input type="number" value={cfg.code ?? ""}
                onChange={(e) => update("code", e.target.value ? Number(e.target.value) : undefined)} />
            </div>
            <div className="field-row">
              <label>测试过滤</label>
              <input value={cfg.test_filter ?? ""} onChange={(e) => update("test_filter", e.target.value || undefined)} />
            </div>
            <div className="field-row">
              <label>测试跳过</label>
              <input value={cfg.test_skip ?? ""} onChange={(e) => update("test_skip", e.target.value || undefined)} />
            </div>
          </Section>

          <Section title="代理设置">
            <div className="field-row">
              <label>代理地址</label>
              <input value={cfg.proxy ?? ""}
                onChange={(e) => update("proxy", e.target.value || undefined)}
                placeholder="如 http://127.0.0.1:7890" />
            </div>
          </Section>

          <Section title="绕过与扩展">
            <div className="field-row">
              <label>Tamper 预设</label>
              <select value={cfg.tamper_preset ?? "关闭"}
                onChange={(e) => applyTamperPreset(e.target.value)}>
                {Object.keys(TAMPER_PRESETS).map((name) => (
                  <option key={name} value={name}>{name}</option>
                ))}
              </select>
            </div>
            {cfg.tamper.length > 0 && (
              <div className="tamper-tags">
                {cfg.tamper.map((t) => <span key={t} className="tamper-tag">{t}</span>)}
              </div>
            )}
            <div className="field-row">
              <label>附加参数</label>
              <input value={cfg.extra_args.join(" ")}
                onChange={(e) => update("extra_args", e.target.value.split(/\s+/).filter(Boolean))}
                placeholder="如 --proxy http://127.0.0.1:8080" />
            </div>
          </Section>

          <Section title="快捷开关">
            <div className="toggle-grid">
              {([
                ["batch", "默认应答 --batch"],
                ["random_agent", "随机 UA"],
                ["force_ssl", "强制 SSL"],
                ["text_only", "仅文本比对"],
                ["skip_waf", "跳过 WAF 检测"],
                ["skip_static", "跳过静态参数"],
                ["smart", "智能探测"],
                ["titles", "标题比对"],
                ["skip_heuristics", "跳过启发式"],
                ["no_cast", "不使用 CAST"],
                ["no_escape", "不转义"],
                ["invalid_bignum", "无效大数"],
                ["invalid_logical", "无效逻辑"],
                ["invalid_string", "无效字符串"],
                ["flush_session", "启动前清空会话"],
                ["eta", "ETA 进度"],
                ["parse_errors", "解析错误"],
              ] as const).map(([key, label]) => (
                <label key={key} className="toggle-item">
                  <input type="checkbox" checked={!!cfg[key]}
                    onChange={(e) => update(key, e.target.checked as never)} />
                  <span>{label}</span>
                </label>
              ))}
            </div>
          </Section>

          <Section title="信息获取与批量">
            <div className="toggle-grid">
              {([
                ["current_db", "当前库 --current-db"],
                ["current_user", "当前用户 --current-user"],
                ["is_dba", "DBA 权限 --is-dba"],
                ["dbs", "枚举库 --dbs"],
                ["tables", "枚举表 --tables"],
                ["columns", "枚举列 --columns"],
                ["dump", "Dump --dump"],
                ["dump_all", "一键脱库 --dump-all"],
                ["batch_url", "批量 URL"],
                ["batch_data", "批量请求包"],
              ] as const).map(([key, label]) => (
                <label key={key} className="toggle-item">
                  <input type="checkbox" checked={!!cfg[key]}
                    onChange={(e) => update(key, e.target.checked as never)} />
                  <span>{label}</span>
                </label>
              ))}
            </div>
          </Section>
            </div>
          </div>
        </aside>

        {/* ── CENTER: Workbench ── */}
        <section className="center-panel">
          <div className="card target-card">
            <div className="card-header">
              <h2>目标 / 数据包输入</h2>
              <div className="input-type-bar">
                {INPUT_TYPE_BUTTONS.map((b) => (
                  <button key={b.value} type="button"
                    className={`seg-btn ${cfg.input_type === b.value ? "active" : ""}`}
                    onClick={() => update("input_type", b.value)}>
                    {b.label}
                  </button>
                ))}
              </div>
            </div>
            <textarea
              className="target-input"
              value={cfg.target}
              onChange={(e) => update("target", e.target.value)}
              rows={8}
              placeholder={cfg.input_type === "raw_request" ? "粘贴原始 HTTP 请求包..." : "输入目标 URL，每行一条"}
            />
            <div className="quick-actions">
              <button type="button" className="ghost-btn" onClick={() => { update("target", URL_EXAMPLE); update("input_type", "url"); }}>
                URL 示例
              </button>
              <button type="button" className="ghost-btn" onClick={() => { update("target", REQUEST_EXAMPLE); update("input_type", "raw_request"); }}>
                请求示例
              </button>
              <button type="button" className="ghost-btn" onClick={() => update("target", "")}>
                清空
              </button>
            </div>
          </div>

          <div className="card preview-card">
            <div className="card-header">
              <h2>命令预览</h2>
              <button type="button" className="ghost-btn"
                onClick={() => { navigator.clipboard.writeText(previewCommand); }}>
                复制
              </button>
            </div>
            <pre className="preview-terminal">{previewCommand}</pre>
          </div>

          <button type="button" className="primary-btn submit-btn" onClick={(e) => submit(e)}>
            启动扫描
          </button>

          {selectedTask && selectedTask.status === "completed" && (
            <div className="card report-card">
              <div className="card-header">
                <h2>导出结果</h2>
                <div className="header-actions">
                  <button type="button" className="ghost-btn" onClick={() => handleExportReport("json")}>
                    导出 JSON
                  </button>
                  <button type="button" className="ghost-btn" onClick={() => handleExportReport("html")}>
                    导出 HTML
                  </button>
                  <button type="button" className="ghost-btn" onClick={() => handleExportReport("markdown")}>
                    导出 Markdown
                  </button>
                </div>
              </div>
              {report && (
                <dl className="report-dl">
                  <dt>状态</dt><dd>{report.summary.status}</dd>
                  <dt>日志行</dt><dd>{report.summary.log_lines}</dd>
                </dl>
              )}
            </div>
          )}

          {Object.values(injectionResults).some(arr => arr.length > 0) && (
            <div className="card results-card">
              <h2>注入结果</h2>
              <div className="results-section">
                {injectionResults.current_db.length > 0 && (
                  <div className="result-group">
                    <h3>当前数据库</h3>
                    <div className="result-tags">
                      {injectionResults.current_db.map((db, i) => (
                        <span key={i} className="result-tag"
                          onClick={() => update("custom_db", db)}
                          title="点击使用此数据库">
                          {db}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {injectionResults.databases.length > 0 && (
                  <div className="result-group">
                    <h3>数据库列表</h3>
                    <div className="result-tags">
                      {injectionResults.databases.map((db, i) => (
                        <span key={i} className="result-tag"
                          onClick={() => update("custom_db", db)}
                          title="点击使用此数据库">
                          {db}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {injectionResults.tables.length > 0 && (
                  <div className="result-group">
                    <h3>表名列表</h3>
                    <div className="result-tags">
                      {injectionResults.tables.map((table, i) => (
                        <span key={i} className="result-tag"
                          onClick={() => update("custom_table", table)}
                          title="点击使用此表名">
                          {table}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {injectionResults.columns.length > 0 && (
                  <div className="result-group">
                    <h3>列名列表</h3>
                    <div className="result-tags">
                      {injectionResults.columns.map((column, i) => (
                        <span key={i} className="result-tag"
                          onClick={() => update("custom_column", column)}
                          title="点击使用此列名">
                          {column}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {selectedTask && selectedTask.status === "completed" && !Object.values(injectionResults).some((arr) => arr.length > 0) && (
            <div className="card results-card">
              <h2>注入结果</h2>
              <p className="muted">暂无可复用结果，可尝试执行 --dbs、--tables、--columns 或导出结果生成结构化报告。</p>
            </div>
          )}
        </section>

        {/* ── RIGHT: Tasks + Log ── */}
        <aside className="right-panel">
          <div className="card task-queue-card">
            <div className="card-header">
              <h2>任务队列</h2>
              <div className="header-actions">
                <button type="button" className="ghost-btn"
                  onClick={() => refreshTasks().catch(() => {})}>
                  刷新
                </button>
                <button type="button" className="ghost-btn danger-btn"
                  onClick={handleClearAllTasks}>
                  清空队列
                </button>
              </div>
            </div>
            <div className="task-list">
              {tasks.map((task) => (
                <div key={task.id} className="task-item-wrapper">
                  <button
                    className={`task-item ${selectedTask?.id === task.id ? "selected" : ""} ${statusClass(task.status)}`}
                    onClick={() => setSelectedTaskId(task.id)}>
                    <span className="task-status">{statusLabel(task.status)}</span>
                    <span className="task-target">{task.target}</span>
                    <small className="task-id">{task.id.slice(0, 8)}</small>
                  </button>
                  {task.status === "running" && (
                    <button
                      className="stop-btn"
                      onClick={() => handleCancelTask(task.id)}
                      disabled={cancellingTaskId === task.id}>
                      {cancellingTaskId === task.id ? "取消中..." : "停止"}
                    </button>
                  )}
                </div>
              ))}
              {tasks.length === 0 && <p className="muted">暂无任务</p>}
            </div>
          </div>

          <div className="card log-card">
            <div className="card-header">
              <h2>实时日志</h2>
              <span className="log-count">{logs.length} 行</span>
            </div>
            <div className="log-terminal" ref={logScrollRef} onScroll={handleLogScroll}>
              {logs.length === 0 && <p className="muted">等待任务输出...</p>}
              {logs.length > MAX_RENDERED_LOG_LINES && (
                <div className="muted log-truncated">仅显示最近 {MAX_RENDERED_LOG_LINES} 行（共 {logs.length} 行）</div>
              )}
              {visibleLogs.map((line, i) => (
                <div key={line.id ?? i} className={`log-line log-${line.level}`}>{line.message}</div>
              ))}
              <div ref={logEndRef} />
            </div>
          </div>
        </aside>
      </div>
    </main>
  );
}
