import type { ReportRead, TaskEvent } from "../types";

/**
 * Live injection-result parsing for running scans. This mirrors the backend's
 * authoritative parser (`reports/service.py`); the backend report is preferred
 * once a task completes, and this runs only as a live/fallback preview.
 */

export type InjectionResults = Record<
  "databases" | "tables" | "columns" | "current_db" | "current_user",
  string[]
>;

export function emptyInjectionResults(): InjectionResults {
  return { databases: [], tables: [], columns: [], current_db: [], current_user: [] };
}

export function resultsFromReport(report: ReportRead): InjectionResults {
  return {
    databases: report.summary.databases ?? [],
    tables: report.summary.tables ?? [],
    columns: report.summary.columns ?? [],
    current_db: report.summary.current_db ?? [],
    current_user: report.summary.current_user ?? [],
  };
}

export function parseInjectionResults(logs: TaskEvent[]): InjectionResults {
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
        const cells = msg.split("|").filter((c) => c.trim());
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
        const cells = msg.split("|").filter((c) => c.trim());
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
