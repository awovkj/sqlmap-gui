from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

from backend.sqlmap_gui.core.artifacts import ArtifactsManager


class ReportService:
    def __init__(self, artifacts: ArtifactsManager):
        self.artifacts = artifacts

    def _parse_injection_results(self, log_lines: list[str]) -> dict[str, list[str]]:
        results: dict[str, list[str]] = {
            "databases": [],
            "tables": [],
            "columns": [],
            "current_db": [],
            "current_user": [],
        }

        phase = "none"

        for line in log_lines:
            stripped = line.strip()
            if stripped.startswith("[*] starting @") or stripped.startswith("[*] ending @"):
                phase = "none"
                continue

            if "fetching database names" in line or "available databases" in line:
                phase = "databases"
                continue
            if "fetching tables for database" in line:
                phase = "tables"
                continue
            if re.search(r"^Table:\s", line) or ("Table:" in line and "[INFO]" not in line):
                phase = "columns"
                continue
            if "dumping data from table" in line:
                phase = "none"
                continue

            if phase == "databases" and "[*]" in line:
                m = re.search(r"\[\*\]\s+([^\s,]+)", line)
                if m:
                    name = m.group(1).strip()
                    if name and name not in results["databases"]:
                        results["databases"].append(name)
                continue

            if phase == "tables":
                if line.startswith("+") and "-" in line:
                    continue
                if line.startswith("|"):
                    cells = [c.strip() for c in line.split("|") if c.strip()]
                    if len(cells) == 1:
                        name = cells[0]
                        if name and name != "Database" and name not in results["tables"]:
                            results["tables"].append(name)
                    continue

            if phase == "columns":
                if line.startswith("+") and "-" in line:
                    continue
                if line.startswith("|"):
                    cells = [c.strip() for c in line.split("|") if c.strip()]
                    if len(cells) >= 2:
                        name = cells[0]
                        if name and name != "Column" and name not in results["columns"]:
                            results["columns"].append(name)
                    continue

            if "[INFO]" in line and phase != "none":
                if "fetching database names" not in line and "available databases" not in line and "fetching tables for database" not in line:
                    phase = "none"

            db_match = re.search(r"current database:\s*['\"]?([^'\"\s,]+)['\"]?", line)
            if db_match:
                name = db_match.group(1).strip()
                if name and name not in results["current_db"]:
                    results["current_db"].append(name)

            user_match = re.search(r"current user:\s*['\"]?([^'\"]+)['\"]?", line)
            if user_match:
                name = user_match.group(1).strip()
                if name and name not in results["current_user"]:
                    results["current_user"].append(name)

        return results

    def _generate_html_report(self, task: dict[str, Any], results: dict[str, list[str]], log_lines: list[str]) -> str:
        esc = html.escape
        target = esc(task["target"])
        status = esc(task["status"])
        exit_code = esc(str(task.get("exit_code", "")))
        task_id = esc(task["id"])

        status_class = "success" if task["status"] == "completed" else "failed"

        db_tags = "".join(f'<span class="tag db">{esc(db)}</span>' for db in results["databases"]) if results["databases"] else '<span class="empty">未发现</span>'
        table_tags = "".join(f'<span class="tag table">{esc(t)}</span>' for t in results["tables"]) if results["tables"] else '<span class="empty">未发现</span>'
        col_tags = "".join(f'<span class="tag col">{esc(c)}</span>' for c in results["columns"]) if results["columns"] else '<span class="empty">未发现</span>'
        cdb_tags = "".join(f'<span class="tag current">{esc(d)}</span>' for d in results["current_db"]) if results["current_db"] else '<span class="empty">未发现</span>'
        user_tags = "".join(f'<span class="tag user">{esc(u)}</span>' for u in results["current_user"]) if results["current_user"] else '<span class="empty">未发现</span>'

        recent_logs = log_lines[-100:]
        log_html = "\n".join(f"<div class='log-line'>{esc(l)}</div>" for l in recent_logs)

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>SQLmap Report - {target}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, "Microsoft YaHei", sans-serif; background: #f5f7fa; color: #1a1a2e; padding: 24px; }}
  .container {{ max-width: 960px; margin: 0 auto; }}
  .header {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 32px; border-radius: 12px; margin-bottom: 24px; }}
  .header h1 {{ font-size: 22px; margin-bottom: 16px; }}
  .meta {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }}
  .meta-item {{ background: rgba(255,255,255,0.15); padding: 12px; border-radius: 8px; }}
  .meta-item label {{ font-size: 11px; opacity: 0.8; display: block; margin-bottom: 4px; }}
  .meta-item span {{ font-size: 14px; font-weight: 600; word-break: break-all; }}
  .status-badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 700; }}
  .status-badge.success {{ background: #10b981; }}
  .status-badge.failed {{ background: #ef4444; }}
  .section {{ background: white; border-radius: 12px; padding: 24px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
  .section h2 {{ font-size: 16px; color: #4a5568; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 2px solid #e2e8f0; }}
  .tag-group {{ margin-bottom: 16px; }}
  .tag-group:last-child {{ margin-bottom: 0; }}
  .tag-group h3 {{ font-size: 13px; color: #718096; margin-bottom: 8px; }}
  .tags {{ display: flex; flex-wrap: wrap; gap: 8px; }}
  .tag {{ display: inline-block; padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: 600; }}
  .tag.db {{ background: #dbeafe; color: #1d4ed8; }}
  .tag.table {{ background: #fef3c7; color: #92400e; }}
  .tag.col {{ background: #d1fae5; color: #065f46; }}
  .tag.current {{ background: #ede9fe; color: #5b21b6; }}
  .tag.user {{ background: #fce7f3; color: #9d174d; }}
  .empty {{ color: #a0aec0; font-style: italic; font-size: 13px; }}
  .log-box {{ background: #1a1a2e; color: #e2e8f0; border-radius: 8px; padding: 16px; max-height: 400px; overflow-y: auto; font-family: "Cascadia Mono", Consolas, monospace; font-size: 12px; line-height: 1.6; }}
  .log-line {{ white-space: pre-wrap; word-break: break-all; }}
  .summary-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }}
  .summary-card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; text-align: center; }}
  .summary-card .num {{ font-size: 28px; font-weight: 800; color: #2563eb; }}
  .summary-card .label {{ font-size: 12px; color: #718096; margin-top: 4px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>SQLmap 注入报告</h1>
    <div class="meta">
      <div class="meta-item"><label>目标</label><span>{target}</span></div>
      <div class="meta-item"><label>状态</label><span><span class="status-badge {status_class}">{status}</span></span></div>
      <div class="meta-item"><label>退出码</label><span>{exit_code}</span></div>
    </div>
  </div>

  <div class="section">
    <h2>注入结果概览</h2>
    <div class="summary-grid">
      <div class="summary-card"><div class="num">{len(results['databases'])}</div><div class="label">数据库</div></div>
      <div class="summary-card"><div class="num">{len(results['tables'])}</div><div class="label">表</div></div>
      <div class="summary-card"><div class="num">{len(results['columns'])}</div><div class="label">列</div></div>
      <div class="summary-card"><div class="num">{len(results['current_db'])}</div><div class="label">当前数据库</div></div>
    </div>
  </div>

  <div class="section">
    <h2>详细结果</h2>
    <div class="tag-group"><h3>数据库列表</h3><div class="tags">{db_tags}</div></div>
    <div class="tag-group"><h3>当前数据库</h3><div class="tags">{cdb_tags}</div></div>
    <div class="tag-group"><h3>当前用户</h3><div class="tags">{user_tags}</div></div>
    <div class="tag-group"><h3>表名列表</h3><div class="tags">{table_tags}</div></div>
    <div class="tag-group"><h3>列名列表</h3><div class="tags">{col_tags}</div></div>
  </div>

  <div class="section">
    <h2>执行日志（最近 100 行）</h2>
    <div class="log-box">{log_html}</div>
  </div>
</div>
</body>
</html>"""

    def _generate_markdown_report(self, task: dict[str, Any], results: dict[str, list[str]], log_lines: list[str]) -> str:
        lines = [
            "# SQLmap 注入报告",
            "",
            f"- **任务**: `{task['id']}`",
            f"- **目标**: `{task['target']}`",
            f"- **状态**: `{task['status']}`",
            f"- **退出码**: `{task.get('exit_code')}`",
            "",
            "## 注入结果",
            "",
        ]

        if results["databases"]:
            lines.append("### 数据库")
            for db in results["databases"]:
                lines.append(f"- `{db}`")
            lines.append("")

        if results["current_db"]:
            lines.append("### 当前数据库")
            for db in results["current_db"]:
                lines.append(f"- `{db}`")
            lines.append("")

        if results["current_user"]:
            lines.append("### 当前用户")
            for u in results["current_user"]:
                lines.append(f"- `{u}`")
            lines.append("")

        if results["tables"]:
            lines.append("### 表名")
            for t in results["tables"]:
                lines.append(f"- `{t}`")
            lines.append("")

        if results["columns"]:
            lines.append("### 列名")
            for c in results["columns"]:
                lines.append(f"- `{c}`")
            lines.append("")

        lines.extend([
            "## 执行日志（最近 100 行）",
            "",
            "```text",
            "\n".join(log_lines[-100:]),
            "```",
            "",
        ])

        return "\n".join(lines)

    def create_basic_report(self, task: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
        task_id = task["id"]
        reports_dir = self.artifacts.reports_dir(task_id)
        log_lines = [event["message"] for event in events if event.get("type") == "log"]
        results = self._parse_injection_results(log_lines)

        summary = {
            "task_id": task_id,
            "target": task["target"],
            "status": task["status"],
            "exit_code": task.get("exit_code"),
            "log_lines": len(log_lines),
            "last_log_line": log_lines[-1] if log_lines else "",
            "databases": results["databases"],
            "tables": results["tables"],
            "columns": results["columns"],
            "current_db": results["current_db"],
            "current_user": results["current_user"],
        }

        json_path = reports_dir / "report.json"
        html_path = reports_dir / "report.html"
        markdown_path = reports_dir / "report.md"

        self.artifacts.write_json(json_path, summary)
        html_path.write_text(self._generate_html_report(task, results, log_lines), encoding="utf-8")
        markdown_path.write_text(self._generate_markdown_report(task, results, log_lines), encoding="utf-8")

        return {
            "summary": summary,
            "json_path": str(json_path),
            "html_path": str(html_path),
            "markdown_path": str(markdown_path),
        }
