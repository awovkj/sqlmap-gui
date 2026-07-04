# 项目全面优化与无关文件清理设计

## 背景

当前仓库已经演进到现代版架构：Electron 桌面入口、React 前端工作台、FastAPI 后端、SQLite 持久化，以及 `vendor/sqlmap/` 中的 sqlmap 核心。但工作区中仍残留旧 GUI、旧框架实验代码、根目录旧 sqlmap 副本、测试产物、运行缓存、截图和本地数据库等内容。这些文件会干扰维护、测试和提交边界。

本次优化目标是把项目收敛到现代版主线，保留可运行、可测试、可维护的代码路径，并删除明确无关或生成性质的文件。

## 目标

- 以 `apps/ + backend/ + vendor/sqlmap/` 为唯一运行主线。
- 保留并验证当前现代版功能，包括任务创建、sqlmap 执行、日志、报告、注入结果展示与复用。
- 删除旧架构、旧副本、运行产物和缓存。
- 更新 `.gitignore`，防止运行数据、构建产物、缓存、截图再次进入版本控制。
- 最终通过后端测试、前端类型检查和前端构建。

## 非目标

- 不重写整体架构。
- 不删除 `vendor/sqlmap/`，因为后端依赖该目录执行 sqlmap。
- 不删除 `node_modules/` 本地目录，仅确保它被忽略。
- 不做大型 UI 视觉重设计。
- 不把运行数据库、扫描结果和本地截图纳入仓库。

## 保留范围

必须保留：

```text
apps/
backend/
vendor/sqlmap/
tests/backend/
tests/frontend/        # 若测试仍有效则保留
scripts/
docs/
package.json
package-lock.json
requirements.txt
tsconfig.json
README.md
LICENSE
```

启动脚本策略：

- 若根目录 `start.bat`、`start.sh`、`启动.bat` 指向现代版 `npm start` / 环境检查，则保留。
- 若它们只是旧 GUI 启动器或重复无效脚本，则删除。

## 删除范围

删除或保持删除以下旧内容：

```text
GUI-CN/
framework/
config/
sqlmap/                 # 根目录旧副本；现代版只使用 vendor/sqlmap/
artifacts/test-run*/
artifacts/tasks/
data/*.sqlite3*
.pytest_cache/
.playwright-mcp/
scroll-*.png
__pycache__/
*.pyc
```

说明：

- `artifacts/tasks/` 和 `data/*.sqlite3*` 是运行时输出，不应提交。
- `scroll-*.png` 是调试截图，不属于产品源码。
- `.playwright-mcp/`、`.pytest_cache/` 是本地工具缓存。
- 根目录 `sqlmap/` 与 `vendor/sqlmap/` 重复，保留 `vendor/sqlmap/` 作为唯一依赖来源。

## 优化策略

### 1. 工作区收敛

先确认当前工作区改动来源，把有效现代版改动纳入本次提交范围，包括：

- 后端任务/report/结果解析相关优化。
- 前端注入结果展示、点击复用、报告导出相关优化。
- 仍有效的测试补充。

### 2. 清理旧路径

按白名单保留现代路径，按黑名单删除旧路径。删除前检查目标路径位于项目根目录内，避免误删外部文件。

### 3. 忽略规则

`.gitignore` 覆盖：

- Python 缓存和测试缓存。
- Node 依赖和构建产物。
- 运行数据库。
- 扫描 artifact。
- 本地工具缓存。
- 调试截图。

### 4. 验证

清理后执行：

```powershell
python -m pytest tests/backend -q
npm run typecheck
npm run build:web
```

若 `tests/frontend` 有有效测试，再运行对应测试或保留其源文件不执行。

## 风险与处理

- 删除旧目录风险：通过保留 `vendor/sqlmap/` 和运行验证降低风险。
- 历史未提交改动混杂风险：使用路径级 diff 和状态检查，只提交预期路径。
- 构建产物变更风险：`apps/web/dist/` 若被构建改变，应作为生成物忽略或不纳入提交。
- 启动脚本误删风险：先检查脚本内容，只有确认无效才删除。

## 验收标准

- 现代版主线文件保留完整。
- 旧 GUI、旧 framework、根目录旧 sqlmap、运行产物和缓存不再出现在工作区。
- `.gitignore` 覆盖运行/构建/缓存文件。
- 后端测试通过。
- 前端类型检查通过。
- Web 构建通过。
- `git status --short` 只显示本次预期源码、测试、文档和清理改动。
