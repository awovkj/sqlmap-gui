import type { ScanConfig } from "../types";

/**
 * Human-facing preview of the sqlmap argv. Mirrors the backend
 * `build_sqlmap_command`; the runtime-only `--output-dir` is omitted here
 * since it is an internal artifact path rather than user input.
 */
export function buildPreviewCommand(cfg: ScanConfig): string {
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
  if (cfg.proxy) args.push("--proxy", cfg.proxy);
  if (cfg.extra_args.length > 0) args.push(...cfg.extra_args);
  return args.join(" ");
}
