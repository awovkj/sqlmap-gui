from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    PARSING = "parsing"
    COMPLETED = "completed"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class ScanConfig(BaseModel):
    # ── Target ──────────────────────────────────────────────
    target: str = Field(min_length=1)
    input_type: Literal["url", "raw_request", "batch_urls", "batch_requests"] = "url"
    request_file: str | None = None

    # ── Preset ──────────────────────────────────────────────
    preset: Literal["balanced", "deep", "waf", "enum_structure", "data_export"] = "balanced"

    # ── Scan Config ─────────────────────────────────────────
    level: int | None = None
    risk: int | None = None
    threads: int | None = None
    batch_workers: int | None = None
    technique: str | None = None
    dbms: str | None = None

    # ── Target Scope ────────────────────────────────────────
    test_parameter: str | None = None
    skip_parameter: str | None = None
    param_exclude: str | None = None
    param_filter: str | None = None
    custom_db: str | None = None
    custom_table: str | None = None
    custom_column: str | None = None

    # ── Injection Control ───────────────────────────────────
    prefix: str | None = None
    suffix: str | None = None
    time_sec: int | None = None
    union_cols: str | None = None
    union_char: str | None = None
    union_from: str | None = None
    union_values: str | None = None

    # ── Detection Control ───────────────────────────────────
    string: str | None = None
    not_string: str | None = None
    regexp: str | None = None
    code: int | None = None
    test_filter: str | None = None
    test_skip: str | None = None

    # ── Tamper ──────────────────────────────────────────────
    tamper: list[str] = Field(default_factory=list)
    tamper_preset: str | None = None

    # ── Boolean Flags ───────────────────────────────────────
    batch: bool = True
    random_agent: bool = True
    force_ssl: bool = False
    text_only: bool = False
    skip_waf: bool = False
    skip_static: bool = False
    smart: bool = False
    titles: bool = False
    skip_heuristics: bool = False
    no_cast: bool = False
    no_escape: bool = False
    invalid_bignum: bool = False
    invalid_logical: bool = False
    invalid_string: bool = False
    flush_session: bool = False
    eta: bool = True
    parse_errors: bool = True

    # ── Enumeration ─────────────────────────────────────────
    current_db: bool = False
    current_user: bool = False
    is_dba: bool = False
    dbs: bool = False
    tables: bool = False
    columns: bool = False
    dump: bool = False
    dump_all: bool = False

    # ── Batch ───────────────────────────────────────────────
    batch_url: bool = False
    batch_data: bool = False

    # ── Extra ───────────────────────────────────────────────
    extra_args: list[str] = Field(default_factory=list)
    proxy: str | None = None


class TaskRead(BaseModel):
    id: str
    project_id: str
    status: TaskStatus
    engine: str
    command: list[str] = Field(default_factory=list)
    output_dir: str
    target: str
    input_type: str
    started_at: str | None = None
    finished_at: str | None = None
    exit_code: int | None = None
    error_message: str | None = None


class TaskEventRead(BaseModel):
    id: int
    task_id: str
    level: str
    type: str
    message: str
    created_at: str


class ReportRead(BaseModel):
    id: int | None = None
    task_id: str
    summary: dict[str, Any] = Field(default_factory=dict)
    json_path: str
    html_path: str
    markdown_path: str
    created_at: str | None = None
