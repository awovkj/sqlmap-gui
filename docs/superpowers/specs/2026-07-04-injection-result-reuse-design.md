# 注入结果可视化复用设计

## 背景

当前 SQLmap GUI 已支持创建任务、实时日志、任务列表、手动导出报告，以及在前端根据日志尝试解析部分注入结果。但用户期望的“结果复用”是：注入完成后，能在界面中直观看到注入出的库名、表名、列名等结果，并且点击结果后直接回填到目标范围参数（`-D`、`-T`、`-C`），继续发起枚举或导出任务。

现状问题：

- 报告目前主要由用户点击“导出结果”触发生成，任务完成后不会稳定自动生成结构化结果。
- 前端已有实时日志解析和结果标签展示雏形，但刷新页面、切换任务或未生成 report 时容易丢失或不完整。
- 结果展示与参数回填依赖前端临时状态，缺少后端持久化结构化结果作为权威来源。

## 目标

- 任务完成后自动生成结构化注入结果。
- 前端在任务完成、刷新页面、切换历史任务后，都能加载并展示已解析结果。
- 结果支持一键复用：
  - 库名或当前库点击后填入 `custom_db`，用于 `-D`。
  - 表名点击后填入 `custom_table`，用于 `-T`。
  - 列名点击后填入 `custom_column`，用于 `-C`。
- 保留前端实时解析作为运行中预览/兜底，不替代后端持久化结果。

## 非目标

- 不改变 sqlmap session/output-dir 复用策略。
- 不解析 sqlmap 内部 `session.sqlite`。
- 不实现库-表-列的严格层级树；本次先提供可复用的扁平结果集合。
- 不新增复杂报告中心，仅优化当前任务详情中的结果展示与回填链路。

## 推荐方案

采用“后端结构化 report 为主，前端实时解析兜底”的方案。

### 后端

1. 在 `TaskManager._run_task` 中，任务结束且状态为 `completed` 时自动调用 `generate_report` 或内部报告生成逻辑。
2. `ReportService` 继续负责从任务事件日志中解析结构化结果，输出到 reports 表和 `artifacts/tasks/<task_id>/reports/report.json`。
3. 增强解析覆盖面，至少支持：
   - `available databases` 后的 `[*] database_name`。
   - `current database: 'xxx'`。
   - `current user: 'xxx'`。
   - sqlmap 表格形式的表名和列名输出。
4. 自动生成报告失败不能影响任务最终状态；失败时记录错误事件，任务仍保持 sqlmap 的完成/失败状态。

### 前端

1. 切换任务后优先调用 `/api/tasks/{id}/report` 获取结构化结果。
2. 如果 report 不存在或任务仍在运行，则用实时日志解析结果作为兜底预览。
3. “注入结果”区域展示：当前数据库、数据库列表、表名列表、列名列表。
4. 点击结果标签立即回填配置：
   - `current_db` 和 `databases` → `custom_db`
   - `tables` → `custom_table`
   - `columns` → `custom_column`
5. `-D/-T/-C` 输入控件继续支持手动输入；当存在结果时提供下拉选择。
6. 回填后命令预览自动更新，因为预览基于 `cfg` 状态生成。

## 数据流

```text
用户启动扫描
→ POST /api/tasks
→ TaskManager 执行 sqlmap
→ 日志写入 task_events + run.log
→ 任务 completed
→ 后端自动生成 report
→ reports 表持久化 summary_json
→ 前端 SSE/刷新任务列表
→ 前端读取 /api/tasks/{id}/report
→ 注入结果卡片展示
→ 用户点击库/表/列标签
→ 写入 cfg.custom_db/custom_table/custom_column
→ 命令预览出现 -D/-T/-C
```

## 错误处理

- report 不存在：前端不报错，改用日志解析或显示暂无结果。
- 自动 report 生成失败：后端写入 error 事件，不覆盖任务状态。
- 解析不到任何结果：展示“暂无可复用结果”，但日志与导出功能仍可用。
- 用户清空任务：同步清空前端结果缓存和当前结果展示。

## 测试策略

### 后端测试

- `ReportService` 能从样例日志中解析数据库列表、当前库、当前用户、表名、列名。
- `TaskManager` 在 fake engine 完成后自动创建 report。
- 自动生成 report 失败时任务状态不被错误覆盖。

### 前端验证

- 已完成任务切换后能显示 report 中的结果。
- 点击数据库标签后 `-D` 输入值变化，命令预览包含 `-D <db>`。
- 点击表名标签后命令预览包含 `-T <table>`。
- 点击列名标签后命令预览包含 `-C <column>`。
- report 缺失时仍可根据日志显示运行中解析结果。

## 迁移与兼容

- 已有历史任务如果没有 report，用户切换任务时仍可通过日志解析临时展示；也可在导出时生成 report。
- 不修改已有 API 返回格式，只复用现有 `/api/tasks/{id}/report` 与 `/api/tasks/{id}/report/generate`。
- 若后续需要独立结果接口，可在本设计基础上新增 `/api/tasks/{id}/results`，但本次不需要。
