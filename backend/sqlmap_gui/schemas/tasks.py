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
    target: str = Field(min_length=1)
    input_type: Literal["url", "raw_request"] = "url"
    request_file: str | None = None
    preset: Literal["balanced", "deep", "waf"] = "balanced"
    level: int | None = None
    risk: int | None = None
    threads: int | None = None
    batch: bool = True
    random_agent: bool = True
    eta: bool = True
    parse_errors: bool = True
    text_only: bool = False
    technique: str | None = None
    dbms: str | None = None
    test_parameter: str | None = None
    tamper: list[str] = Field(default_factory=list)
    extra_args: list[str] = Field(default_factory=list)


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
