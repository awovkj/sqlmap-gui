# SQLmap GUI 全量重构设计

## 目标

将当前 Python/Tkinter 形态的 SQLmap GUI 重构为现代桌面应用：保留桌面入口，使用 Electron 承载 React 工作台界面，使用 Python FastAPI 后端统一管理任务、数据库、报告和 sqlmap 子进程。核心扫描能力以 `C:\Users\31373\Downloads\sqlmap-master` 为参考源，同步到项目内置 `vendor/sqlmap/` 后通过命令行方式调用，最大程度保持 sqlmap 原生行为。

## 当前项目观察

- 当前仓库包含 `GUI-CN/`、`framework/`、`sqlmap/`、`config/`、`tests/` 等目录。
- 当前 GUI 主体为 `GUI-CN/gui_shared.py`，单文件体量较大，包含 UI、命令构建、进程管理、日志展示和批量任务逻辑。
- 当前 GUI 启动路径引用 `framework/cli.py`，但该文件不存在，说明现有新框架入口不完整。
- `framework/` 已有请求解析、参数提取、差异分析、调度、配置和报告雏形，但不适合作为新主线直接保留。
- 当前内置 `sqlmap/` 与参考目录 `C:\Users\31373\Downloads\sqlmap-master` 不一致；运行版本观察为当前内置 `1.10.4.4#dev`，参考目录为 `1.10.6.143#dev`。
- 现有测试基线可运行：`python -m pytest -q` 结果为 `3 passed`。

## 已确认的关键决策

- 桌面形态：Electron + Python 后端。
- 前端技术栈：React + TypeScript + Vite + Tailwind。
- 后端通信：FastAPI + WebSocket/SSE。
- 主界面布局：专业工作台布局。
- sqlmap 集成：用 `C:\Users\31373\Downloads\sqlmap-master` 同步替换项目内置核心，后端默认通过 subprocess 调用 `sqlmap.py`。
- 旧 `framework/` 策略：不作为主线保留，只迁移成熟的请求解析、参数提取和报告辅助逻辑。
- 持久化：SQLite + `artifacts/` 文件产物。
- 打包目标：Windows 优先，保留 Linux/macOS 扩展余地。
- 总体路线：分层平台化重构。

## 总体架构

```text
Electron Desktop
  ├─ 启动/停止 Python 后端
  ├─ 管理桌面窗口、菜单、打包和诊断页
  └─ 加载 React 工作台

React Workbench
  ├─ 项目、目标、请求包、模板、任务、报告界面
  ├─ 通过 REST 创建和查询任务
  └─ 通过 WebSocket/SSE 接收任务状态和实时日志

FastAPI Backend
  ├─ API 路由：项目、目标、任务、模板、报告、设置
  ├─ SQLite 数据层
  ├─ 任务队列与状态机
  ├─ 日志事件分发
  ├─ 报告生成
  └─ SqlmapEngine 子进程适配

vendor/sqlmap
  └─ 从 C:\Users\31373\Downloads\sqlmap-master 同步来的 sqlmap 原生核心
```

该架构保持 UI、业务编排、扫描核心三者边界清晰：前端不直接执行命令，Electron 不承载业务逻辑，后端通过 `SqlmapEngine` 隔离 sqlmap 调用细节。

## 文件结构

```text
sqlmap-gui/
├─ apps/
│  ├─ desktop/              # Electron 主进程、窗口、Python 后端启动器
│  └─ web/                  # React + TS + Vite + Tailwind 工作台 UI
├─ backend/
│  └─ sqlmap_gui/
│     ├─ api/               # FastAPI 路由：项目、任务、模板、报告、设置
│     ├─ core/              # 配置、路径、日志、生命周期
│     ├─ db/                # SQLite 初始化、迁移、Repository
│     ├─ engine/            # SqlmapEngine：subprocess 调用 sqlmap.py
│     ├─ tasks/             # 队列、状态机、实时日志分发
│     ├─ parser/            # 请求包解析、参数提取
│     ├─ reports/           # JSON/HTML/Markdown 报告生成
│     └─ schemas/           # API DTO / Pydantic 模型
├─ vendor/
│  └─ sqlmap/               # 从 sqlmap-master 同步而来
├─ data/
│  └─ sqlmap-gui.sqlite3    # 项目、任务、历史、模板
├─ artifacts/               # sqlmap output、日志、报告文件
├─ docs/                    # 设计、计划、用户文档
├─ tests/
│  ├─ backend/
│  └─ e2e/
└─ legacy/
   ├─ tkinter-gui/          # 原 GUI-CN 归档
   └─ framework/            # 未迁移的旧 framework 代码归档
```

## 组件边界

- **Electron Desktop**：负责窗口、菜单、托盘、启动/停止 Python 后端、端口发现、健康检查、Windows 打包和诊断页。
- **React Web**：负责界面、表单、状态展示、日志终端、报告阅读，不直接执行 sqlmap。
- **FastAPI Backend**：作为唯一业务入口，负责任务、数据库、报告、实时事件、配置和路径管理。
- **SqlmapEngine**：负责构建参数数组、启动 `vendor/sqlmap/sqlmap.py`、管理子进程、读取 stdout/stderr、返回退出码。
- **ArtifactsManager**：统一管理每个任务的日志、命令快照、sqlmap 原始输出和报告目录。
- **Migration Layer**：迁移当前 `framework/` 中成熟的请求解析、参数提取和报告辅助代码；其余代码归档到 `legacy/`。

## 数据流与任务生命周期

```text
用户输入目标/请求包
→ React 表单构建 ScanConfig
→ FastAPI 校验并写入 SQLite
→ TaskQueue 创建任务
→ SqlmapEngine 构建 sqlmap 参数数组
→ subprocess 启动 vendor/sqlmap/sqlmap.py
→ LogStreamer 逐行读取 stdout/stderr
→ WebSocket/SSE 推送日志与状态
→ ArtifactsManager 写入 artifacts/tasks/<task_id>/
→ ResultParser 汇总 sqlmap 输出
→ ReportService 生成 JSON/HTML/Markdown 报告
→ React 报告中心展示历史结果
```

任务状态机：

```text
created → queued → running → parsing → completed

created/queued/running → cancelling → cancelled
running/parsing → failed
running → interrupted
```

关键行为：

- 每个任务拥有独立 `task_id`、输出目录、日志文件和命令快照。
- 批量扫描生成多个任务进入队列，由后端统一并发控制。
- 实时日志既推送到 UI，也持久化到 `artifacts/tasks/<task_id>/run.log`。
- 前端刷新或应用重启后，可从 SQLite 恢复任务历史与报告路径。
- 任务终止由后端管理子进程，避免遗留 sqlmap 进程。
- 普通任务默认使用 `--batch`；交互型 `--sql-shell`、`--os-shell` 后续通过专门终端模式承载。

## API 草案

```text
GET    /api/health

GET    /api/projects
POST   /api/projects
GET    /api/projects/{id}
PATCH  /api/projects/{id}

GET    /api/targets
POST   /api/targets
POST   /api/targets/import

GET    /api/templates
POST   /api/templates
PATCH  /api/templates/{id}
DELETE /api/templates/{id}

POST   /api/tasks
POST   /api/tasks/batch
GET    /api/tasks
GET    /api/tasks/{id}
POST   /api/tasks/{id}/cancel
POST   /api/tasks/{id}/rerun
GET    /api/tasks/{id}/logs
GET    /api/tasks/{id}/report

GET    /api/reports
GET    /api/reports/{id}

GET    /api/settings
PATCH  /api/settings

WS/SSE /api/events
```

## 界面设计

主界面采用专业工作台布局：

```text
┌──────────────────────────────────────────────────────────────┐
│ 顶栏：项目选择 / 新建扫描 / 全局状态 / 设置 / 主题            │
├───────────────┬─────────────────────────┬────────────────────┤
│ 左侧资源栏     │ 中央扫描工作台             │ 右侧实时面板         │
│ - 项目         │ - 目标输入/请求包导入       │ - 当前任务状态       │
│ - 目标资产     │ - 参数预设                 │ - 实时日志终端       │
│ - 请求包库     │ - sqlmap 参数分组          │ - 命令预览           │
│ - 历史任务     │ - 批量队列设置             │ - 风险/发现摘要      │
├───────────────┴─────────────────────────┴────────────────────┤
│ 底部：任务队列 / 最近报告 / 后端健康状态 / sqlmap 版本        │
└──────────────────────────────────────────────────────────────┘
```

一级页面：

- **Dashboard**：项目总览、最近任务、风险统计、后端/sqlmap 状态。
- **New Scan**：目标输入、请求包导入、参数配置、命令预览、启动任务。
- **Tasks**：队列、运行中、已完成、失败、取消；支持过滤、详情、重跑。
- **Reports**：报告中心，支持打开 JSON/HTML/Markdown、导出、搜索。
- **Templates**：扫描预设、tamper 组合、常用参数模板。
- **Settings**：Python 路径、sqlmap 路径、并发、输出目录、主题、更新策略。

首版界面闭环：

1. 创建项目或使用默认项目。
2. 输入单 URL、粘贴原始 HTTP 请求或导入多个请求包。
3. 选择扫描预设与常用 sqlmap 参数。
4. 启动任务并查看实时日志。
5. 任务完成后打开报告与原始输出目录。

## sqlmap 参数与核心集成

核心策略：

- `vendor/sqlmap/` 由 `C:\Users\31373\Downloads\sqlmap-master` 同步生成。
- 后端不直接修改 sqlmap 内部源码，通过 `SqlmapEngine` 构建参数数组并启动 `sqlmap.py`。
- GUI 参数映射到 sqlmap 原生命令行参数，命令预览与实际执行保持一致。
- 保留 `extra_args` 高级输入，允许追加未被 UI 覆盖的原生 sqlmap 参数。

参数分组：

```text
Target
- -u / -r / -m
- --method / --data / --cookie / --headers

Request
- --proxy / --proxy-cred
- --random-agent / --user-agent
- --force-ssl / --timeout / --retries

Detection
- --level / --risk
- --string / --not-string / --regexp / --code
- --smart / --text-only / --titles

Injection
- -p / --skip / --param-exclude
- --dbms / --os
- --technique
- --tamper

Enumeration
- --current-user / --current-db / --is-dba
- --dbs / --tables / --columns / --dump / --dump-all
- -D / -T / -C

Performance & General
- --threads
- --batch
- --flush-session
- --output-dir
- --eta
- --parse-errors

Advanced
- extra_args 原样追加
```

预设策略：

- **平衡测试**：`--batch --random-agent --level 3 --risk 2 --threads 6 --eta --parse-errors`
- **深度测试**：`--batch --random-agent --level 5 --risk 3 --threads 10 --eta --parse-errors`
- **WAF 绕过**：`--batch --random-agent --level 4 --risk 2 --text-only --tamper=<组合> --skip-waf`
- **枚举结构**：在检测基础上追加 `--dbs`、`--tables` 或 `--columns`
- **数据导出**：在用户明确选择后追加 `--dump` 或 `--dump-all`

执行约束：

- 每个任务生成独立 `--output-dir artifacts/tasks/<task_id>/sqlmap-output`。
- 默认追加 `--batch`，除非进入专门的交互任务模式。
- 命令构建使用参数数组，不拼接 shell 字符串，避免空格、引号和中文路径问题。
- 日志解析只作为增强展示，最终以 sqlmap 原始输出和退出码为准。
- `--purge`、`--update` 等全局影响命令放到 Settings/维护页，不混入普通任务。

未来扩展：

- `SqlmapEngine` 接口保留 `SubprocessSqlmapEngine` 与未来 `SqlmapApiEngine`。
- 可从 `vendor/sqlmap/lib/parse/cmdline.py` 提取参数元数据，生成 UI 帮助文本或参数搜索面板。
- tamper 列表从 `vendor/sqlmap/tamper/*.py` 动态读取。

## 数据模型

SQLite 核心表：

```text
projects
- id, name, description, created_at, updated_at

targets
- id, project_id, type, value, label, source, created_at

scan_templates
- id, name, description, config_json, created_at, updated_at

tasks
- id, project_id, target_id, status, engine, command_json,
  output_dir, started_at, finished_at, exit_code, error_message

task_events
- id, task_id, level, type, message, created_at

reports
- id, task_id, summary_json, json_path, html_path, markdown_path, created_at
```

文件产物：

```text
artifacts/
└─ tasks/
   └─ <task_id>/
      ├─ command.json
      ├─ run.log
      ├─ sqlmap-output/
      └─ reports/
         ├─ report.json
         ├─ report.html
         └─ report.md
```

## 报告设计

报告包含：

- 基本信息：目标、任务 ID、开始/结束时间、sqlmap 版本、退出码。
- 命令快照：实际执行参数数组，便于复现。
- 结果摘要：检测到的注入、DBMS、数据库/表/列枚举摘要。
- 原始输出入口：保留 sqlmap 原始目录链接。
- 风险提示：基于 sqlmap 日志关键词和输出结构做轻量分类，不伪造结论。
- 导出格式：JSON 供机器读取，HTML 供阅读，Markdown 供记录或提交。

## 错误处理

- 后端启动失败：Electron 显示诊断页，列出 Python 路径、端口、依赖缺失和启动日志。
- sqlmap 路径失效：Settings 标红，任务创建失败并给出修复入口。
- 任务失败：保存退出码、最后 N 行日志、异常栈到 `task_events`。
- 前端断线：显示“后端连接中断”，自动重连并从 `/api/tasks/{id}/logs` 补历史日志。
- 子进程遗留：后端启动时扫描自身记录的 running 任务，将其标记为 interrupted。
- 数据库损坏：启动前备份损坏文件为 `.broken-<timestamp>`，重新初始化空库。
- 报告解析失败：任务仍可 completed，但报告标记为 partial，并保留原始输出入口。

## 测试策略

- 后端单元测试：命令构建、参数校验、状态机、SQLite Repository、报告生成。
- 后端集成测试：创建任务、运行可控 dummy engine、日志流持久化、取消任务。
- 前端组件测试：扫描表单、命令预览、任务列表、日志终端、报告卡片。
- 端到端测试：Electron 启动、后端健康检查、创建任务、实时日志、报告生成。
- 回归测试：迁移后的请求解析与参数提取逻辑对齐现有 `tests/unit` 行为。

## 分阶段落地

### Phase 1：核心平台闭环

目标：新架构能启动、创建任务、调用 sqlmap、实时显示日志、生成基础报告。

验收标准：

- `npm start` 能启动 Electron。
- Electron 自动启动 Python FastAPI 后端并完成健康检查。
- React 工作台能输入单 URL 或原始请求。
- 后端能创建任务并调用 `vendor/sqlmap/sqlmap.py`。
- UI 能实时显示日志。
- 任务完成后 `artifacts/tasks/<task_id>/` 有 `command.json`、`run.log`、`reports/report.json`。
- SQLite 能保存任务历史。
- 旧 GUI 不再作为默认入口。

### Phase 2：批量与项目管理

目标：支持项目、目标资产、请求包库、批量队列。

验收标准：

- 能创建和切换项目。
- 能导入多个 URL 或多个请求包。
- 批量任务按并发限制执行。
- Tasks 页面可过滤状态、查看详情、取消运行中任务。
- 重启应用后历史任务仍可查看。

### Phase 3：报告中心与模板

目标：提升日常使用效率和结果阅读体验。

验收标准：

- Reports 页面支持 JSON/HTML/Markdown 报告打开与导出。
- Templates 页面支持保存和复用扫描配置。
- tamper 列表从 `vendor/sqlmap/tamper` 动态读取。
- 命令预览与实际执行命令一致。
- 报告包含 sqlmap 版本、参数快照、输出目录链接。

### Phase 4：高级与打包

目标：完成桌面软件体验。

验收标准：

- Windows 打包产物可运行。
- Settings 支持 Python/sqlmap 路径、输出目录、并发配置。
- 后端异常、依赖缺失、端口冲突有诊断页。
- 支持更新 `vendor/sqlmap` 的维护流程。
- 保留 Linux/macOS 路径设计，但 Windows 为首要验收平台。

## 首轮不实现但保留设计入口

- `sqlmapapi.py` engine。
- 交互式 `sql-shell` / `os-shell` 专用终端模式。
- 自动在线更新 GUI。
- 复杂漏洞知识库或协作平台。

