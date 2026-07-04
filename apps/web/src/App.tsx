import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { cancelTask, clearAllTasks, createTask, downloadReport, generateTaskReport, getTaskLogs, getTaskReport, health, listTasks, subscribeEvents } from "./api";
import type {
  InputType,
  ParamFilterType,
  Preset,
  ReportRead,
  ScanConfig,
  TaskEvent,
  TaskRead,
} from "./types";

/* ── Constants ──────────────────────────────────────────── */

const TECHNIQUES = [
  { value: "BESUTQ", label: "全部" },
  { value: "B", label: "布尔盲注" },
  { value: "E", label: "报错注入" },
  { value: "S", label: "堆叠注入" },
  { value: "U", label: "联合注入" },
  { value: "T", label: "时间盲注" },
  { value: "Q", label: "内联查询" },
];

const DBMS_OPTIONS = [
  "", "Altibase", "Amazon Redshift", "Apache Derby", "Apache Ignite", "Aurora", "ClickHouse",
  "CockroachDB", "CrateDB", "Cubrid", "Drizzle", "EnterpriseDB", "eXtremeDB", "Firebird",
  "FrontBase", "Greenplum", "H2", "HSQLDB", "IBM DB2", "Informix", "InterSystems Cache",
  "Iris", "MariaDB", "Mckoi", "MemSQL", "Microsoft Access", "Microsoft SQL Server", "MimerSQL",
  "MonetDB", "MySQL", "OpenGauss", "Oracle", "Percona", "PostgreSQL", "Presto",
  "Raima Database Manager", "SAP MaxDB", "SQLite", "Sybase", "TiDB", "Vertica", "Virtuoso",
  "Yellowbrick", "YugabyteDB",
];

const PARAM_FILTER_OPTIONS: Array<{ value: ParamFilterType; label: string }> = [
  { value: "", label: "不限" },
  { value: "GET", label: "GET" },
  { value: "POST", label: "POST" },
  { value: "COOKIE", label: "COOKIE" },
  { value: "USER-AGENT", label: "User-Agent" },
  { value: "REFERER", label: "Referer" },
  { value: "HOST", label: "Host" },
];

const TAMPER_PRESETS: Record<string, string[]> = {
  "关闭": [],
  "通用绕过": ["between", "randomcase", "space2comment"],
  "编码绕过": ["charencode", "chardoubleencode", "charunicodeencode"],
  "WAF 强化": ["between", "randomcase", "randomcomments", "space2comment", "charencode"],
  "MySQL 定向": ["space2mysqlblank", "space2mysqldash", "versionedkeywords"],
  "MSSQL 定向": ["space2mssqlblank", "space2mssqlhash", "between"],
};

const PRESETS: Array<{ value: Preset; label: string; description: string }> = [
  { value: "balanced", label: "平衡测试", description: "level 3 / risk 2 / threads 6" },
  { value: "deep", label: "深度测试", description: "level 5 / risk 3 / threads 10" },
  { value: "waf", label: "WAF 绕过", description: "text-only + tamper 组合" },
  { value: "enum_structure", label: "枚举结构", description: "level 3 + dbs + tables" },
  { value: "data_export", label: "数据导出", description: "level 3 + dump-all" },
];

const URL_EXAMPLE = "http://127.0.0.1/vul/sqli/sqli_id.php?id=1";
const REQUEST_EXAMPLE = `POST /vul/sqli/sqli_id.php HTTP/1.1
Host: 127.0.0.1
User-Agent: Mozilla/5.0
Content-Type: application/x-www-form-urlencoded
Cookie: PHPSESSID=test

id=1&submit=查询`;

/* ── Defaults ───────────────────────────────────────────── */

function defaultConfig(): ScanConfig {
  return {
    target: "",
    input_type: "url",
    preset: "balanced",
    level: 1,
    risk: 1,
    threads: 10,
    batch_workers: 5,
    technique: "BESUTQ",
    dbms: "",
    test_parameter: "",
    skip_parameter: "",
    param_exclude: "",
    param_filter: "",
    custom_db: "",
    custom_table: "",
    custom_column: "",
    prefix: "",
    suffix: "",
    time_sec: undefined,
    union_cols: "",
    union_char: "",
    union_from: "",
    union_values: "",
    string: "",
    not_string: "",
    regexp: "",
    code: undefined,
    test_filter: "",
    test_skip: "",
    tamper: [],
    tamper_preset: "通用绕过",
    batch: true,
    random_agent: true,
    force_ssl: false,
    text_only: false,
    skip_waf: false,
    skip_static: false,
    smart: false,
    titles: false,
    skip_heuristics: false,
    no_cast: false,
    no_escape: false,
    invalid_bignum: false,
    invalid_logical: false,
    invalid_string: false,
    flush_session: false,
    eta: true,
    parse_errors: true,
    current_db: false,
    current_user: false,
    is_dba: false,
    dbs: false,
    tables: false,
    columns: false,
    dump: false,
    dump_all: false,
    batch_url: false,
    batch_data: false,
    extra_args: [],
    proxy: "",
  };
}

/* ── Helpers ────────────────────────────────────────────── */

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

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    created: "已创建",
    queued: "排队中",
    running: "运行中",
    parsing: "解析中",
    completed: "已完成",
    failed: "失败",
    cancelling: "取消中",
    cancelled: "已取消",
    interrupted: "已中断",
  };
  return labels[status] ?? status;
}

function statusClass(status: string): string {
  if (status === "running") return "status-running";
  if (status === "completed") return "status-done";
  if (status === "failed") return "status-fail";
  if (status === "cancelled" || status === "interrupted") return "status-warn";
  return "";
}

function buildPreviewCommand(cfg: ScanConfig): string {
  const args: string[] = ["python", "-u", "sqlmap.py"];
  if (cfg.input_type === "raw_request") {
    args.push("-r", "<request-file>");
  } else {
    args.push("-u", cfg.target || "<target-url>");
  }
  if (cfg.batch) args.push("--batch");
  if (cfg.random_agent) args.push("--random-agent");
  if (cfg.level != null && cfg.level > 0) args.push("--level", String(cfg.level));
  if (cfg.risk != null && cfg.risk > 0) args.push("--risk", String(cfg.risk));
  if (cfg.threads) args.push("--threads", String(cfg.threads));
  if (cfg.technique && cfg.technique !== "BESUTQ") args.push("--technique", cfg.technique);
  if (cfg.dbms) args.push("--dbms", cfg.dbms);
  if (cfg.test_parameter) args.push("-p", cfg.test_parameter);
  if (cfg.skip_parameter) args.push("--skip", cfg.skip_parameter);
  if (cfg.param_exclude) args.push("--param-exclude", cfg.param_exclude);
  if (cfg.param_filter) args.push("--param-filter", cfg.param_filter);
  if (cfg.custom_db) args.push("-D", cfg.custom_db);
  if (cfg.custom_table) args.push("-T", cfg.custom_table);
  if (cfg.custom_column) args.push("-C", cfg.custom_column);
  if (cfg.prefix) args.push("--prefix", cfg.prefix);
  if (cfg.suffix) args.push("--suffix", cfg.suffix);
  if (cfg.time_sec) args.push("--time-sec", String(cfg.time_sec));
  if (cfg.union_cols) args.push("--union-cols", cfg.union_cols);
  if (cfg.union_char) args.push("--union-char", cfg.union_char);
  if (cfg.union_from) args.push("--union-from", cfg.union_from);
  if (cfg.union_values) args.push("--union-values", cfg.union_values);
  if (cfg.string) args.push("--string", cfg.string);
  if (cfg.not_string) args.push("--not-string", cfg.not_string);
  if (cfg.regexp) args.push("--regexp", cfg.regexp);
  if (cfg.code) args.push("--code", String(cfg.code));
  if (cfg.test_filter) args.push("--test-filter", cfg.test_filter);
  if (cfg.test_skip) args.push("--test-skip", cfg.test_skip);
  if (cfg.tamper.length > 0) args.push("--tamper", cfg.tamper.join(","));
  if (cfg.force_ssl) args.push("--force-ssl");
  if (cfg.text_only) args.push("--text-only");
  if (cfg.skip_waf) args.push("--skip-waf");
  if (cfg.skip_static) args.push("--skip-static");
  if (cfg.smart) args.push("--smart");
  if (cfg.titles) args.push("--titles");
  if (cfg.skip_heuristics) args.push("--skip-heuristics");
  if (cfg.no_cast) args.push("--no-cast");
  if (cfg.no_escape) args.push("--no-escape");
  if (cfg.invalid_bignum) args.push("--invalid-bignum");
  if (cfg.invalid_logical) args.push("--invalid-logical");
  if (cfg.invalid_string) args.push("--invalid-string");
  if (cfg.flush_session) args.push("--flush-session");
  if (cfg.eta) args.push("--eta");
  if (cfg.parse_errors) args.push("--parse-errors");
  if (cfg.current_db) args.push("--current-db");
  if (cfg.current_user) args.push("--current-user");
  if (cfg.is_dba) args.push("--is-dba");
  if (cfg.dbs) args.push("--dbs");
  if (cfg.tables) args.push("--tables");
  if (cfg.columns) args.push("--columns");
  if (cfg.dump) args.push("--dump");
  if (cfg.dump_all) args.push("--dump-all");
  if (cfg.extra_args.length > 0) args.push(...cfg.extra_args);
  return args.join(" ");
}

/* ── Section component ──────────────────────────────────── */

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="param-section">
      <div className="param-section-header">{title}</div>
      <div className="param-section-body">{children}</div>
    </div>
  );
}

function SelectOrInput({
  value,
  onChange,
  options,
  placeholder,
}: {
  value: string;
  onChange: (val: string) => void;
  options: string[];
  placeholder?: string;
}) {
  const [customMode, setCustomMode] = useState(false);

  useEffect(() => {
    if (value && options.length > 0 && !options.includes(value)) {
      setCustomMode(true);
    }
  }, [value, options]);

  if (customMode || options.length === 0) {
    return (
      <div className="select-or-input">
        <input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
        />
        {options.length > 0 && (
          <button type="button" className="toggle-mode-btn" onClick={() => setCustomMode(false)}>
            选择
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="select-or-input">
      <select
        value={options.includes(value) ? value : ""}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">-- 请选择 --</option>
        {options.map((opt) => (
          <option key={opt} value={opt}>{opt}</option>
        ))}
      </select>
      <button type="button" className="toggle-mode-btn" onClick={() => setCustomMode(true)}>
        自定义
      </button>
    </div>
  );
}

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
  const logEndRef = useRef<HTMLDivElement>(null);

  const selectedTask = useMemo(
    () => tasks.find((t) => t.id === selectedTaskId) ?? tasks[0] ?? null,
    [selectedTaskId, tasks],
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
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

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

  function parseInjectionResults(logs: TaskEvent[]): InjectionResults {
    const results = emptyInjectionResults();

    let phase: "none" | "databases" | "tables" | "columns" = "none";

    for (const log of logs) {
      const msg = log.message;
      const trimmed = msg.trim();

      if (trimmed.startsWith("[*] starting @") || trimmed.startsWith("[*] ending @")) {
        phase = "none";
        continue;
      }

      // ── Phase entries ──
      if (msg.includes("fetching database names") || msg.includes("available databases")) {
        phase = "databases";
        continue;
      }
      if (msg.includes("[INFO] fetching tables for database")) {
        phase = "tables";
        continue;
      }
      if (/^Table:\s/.test(msg) || (msg.includes("Table:") && !msg.includes("[INFO]"))) {
        phase = "columns";
        continue;
      }
      if (msg.includes("[INFO] dumping data from table")) {
        phase = "none";
        continue;
      }

      // ── Phase-specific parsing (BEFORE exit check) ──
      if (phase === "databases" && msg.includes("[*]")) {
        const m = msg.match(/\[\*\]\s+([^\s,]+)/);
        if (m) {
          const name = m[1].trim();
          if (name && !results.databases.includes(name)) {
            results.databases.push(name);
          }
        }
        continue;
      }

      if (phase === "tables") {
        if (msg.startsWith("+") && msg.includes("-")) continue;
        if (msg.startsWith("|")) {
          const cells = msg.split("|").filter(c => c.trim());
          if (cells.length === 1) {
            const name = cells[0].trim();
            if (name && name !== "Database" && !results.tables.includes(name)) {
              results.tables.push(name);
            }
          }
          continue;
        }
      }

      if (phase === "columns") {
        if (msg.startsWith("+") && msg.includes("-")) continue;
        if (msg.startsWith("|")) {
          const cells = msg.split("|").filter(c => c.trim());
          if (cells.length >= 2) {
            const name = cells[0].trim();
            if (name && name !== "Column" && !results.columns.includes(name)) {
              results.columns.push(name);
            }
          }
          continue;
        }
      }

      // ── Exit phase on [INFO] (after phase-specific parsing) ──
      if (msg.includes("[INFO]") && phase !== "none") {
        if (!msg.includes("fetching database names") && !msg.includes("available databases") &&
            !msg.includes("fetching tables for database")) {
          phase = "none";
        }
      }

      // ── Always parse current DB/user ──
      const dbMatch = msg.match(/current database:\s*['"]?([^'"\s,]+)['"]?/);
      if (dbMatch) {
        const name = dbMatch[1].trim();
        if (name && !results.current_db.includes(name)) {
          results.current_db.push(name);
        }
      }
      const userMatch = msg.match(/current user:\s*['"]?([^'\"]+)['"]?/);
      if (userMatch) {
        const name = userMatch[1].trim();
        if (name && !results.current_user.includes(name)) {
          results.current_user.push(name);
        }
      }
    }

    return results;
  }

  /* ── Render ──────────────────────────────────────────── */

  const inputTypeButtons: Array<{ value: InputType; label: string }> = [
    { value: "url", label: "单 URL" },
    { value: "raw_request", label: "原始请求" },
    { value: "batch_urls", label: "批量 URL" },
    { value: "batch_requests", label: "批量请求包" },
  ];

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
                {inputTypeButtons.map((b) => (
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
                onClick={() => { navigator.clipboard.writeText(buildPreviewCommand(cfg)); }}>
                复制
              </button>
            </div>
            <pre className="preview-terminal">{buildPreviewCommand(cfg)}</pre>
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
            <div className="log-terminal">
              {logs.length === 0 && <p className="muted">等待任务输出...</p>}
              {logs.map((line, i) => (
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
