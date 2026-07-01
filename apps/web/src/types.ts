export type InputType = "url" | "raw_request";
export type Preset = "balanced" | "deep" | "waf";

export interface ScanConfig {
  target: string;
  input_type: InputType;
  preset: Preset;
  extra_args: string[];
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
  };
  json_path: string;
  html_path: string;
  markdown_path: string;
  created_at: string;
}
