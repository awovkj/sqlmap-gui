export type InputType = "url" | "raw_request" | "batch_urls" | "batch_requests";
export type Preset = "balanced" | "deep" | "waf" | "enum_structure" | "data_export";
export type ParamFilterType = "" | "GET" | "POST" | "COOKIE" | "USER-AGENT" | "REFERER" | "HOST";

export interface ScanConfig {
  target: string;
  input_type: InputType;
  request_file?: string;
  preset: Preset;

  /* Scan Config */
  level?: number;
  risk?: number;
  threads?: number;
  batch_workers?: number;
  technique?: string;
  dbms?: string;

  /* Target Scope */
  test_parameter?: string;
  skip_parameter?: string;
  param_exclude?: string;
  param_filter?: string;
  custom_db?: string;
  custom_table?: string;
  custom_column?: string;

  /* Injection Control */
  prefix?: string;
  suffix?: string;
  time_sec?: number;
  union_cols?: string;
  union_char?: string;
  union_from?: string;
  union_values?: string;

  /* Detection Control */
  string?: string;
  not_string?: string;
  regexp?: string;
  code?: number;
  test_filter?: string;
  test_skip?: string;

  /* Tamper */
  tamper: string[];
  tamper_preset?: string;

  /* Boolean Flags */
  batch: boolean;
  random_agent: boolean;
  force_ssl: boolean;
  text_only: boolean;
  skip_waf: boolean;
  skip_static: boolean;
  smart: boolean;
  titles: boolean;
  skip_heuristics: boolean;
  no_cast: boolean;
  no_escape: boolean;
  invalid_bignum: boolean;
  invalid_logical: boolean;
  invalid_string: boolean;
  flush_session: boolean;
  eta: boolean;
  parse_errors: boolean;

  /* Enumeration */
  current_db: boolean;
  current_user: boolean;
  is_dba: boolean;
  dbs: boolean;
  tables: boolean;
  columns: boolean;
  dump: boolean;
  dump_all: boolean;

  /* Batch */
  batch_url: boolean;
  batch_data: boolean;

  /* Extra */
  extra_args: string[];
  proxy?: string;
}

export interface TaskRead {
  id: string;
  project_id: string;
  status: string;
  engine: string;
  command: string[];
  output_dir: string;
  target: string;
  input_type: string;
  started_at: string | null;
  finished_at: string | null;
  exit_code: number | null;
  error_message: string | null;
}

export interface TaskEvent {
  id: number;
  task_id: string;
  level: string;
  type: string;
  message: string;
  created_at?: string;
  status?: string;
}

export interface ReportRead {
  id: number;
  task_id: string;
  summary: {
    task_id: string;
    target: string;
    status: string;
    exit_code: number | null;
    log_lines: number;
    last_log_line: string;
    databases: string[];
    tables: string[];
    columns: string[];
    current_db: string[];
    current_user: string[];
  };
  json_path: string;
  html_path: string;
  markdown_path: string;
  created_at: string;
}
