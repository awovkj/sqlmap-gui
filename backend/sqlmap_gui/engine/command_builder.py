from __future__ import annotations

from pathlib import Path

from backend.sqlmap_gui.schemas.tasks import ScanConfig


PRESET_DEFAULTS = {
    "balanced": {"level": 3, "risk": 2, "threads": 6, "text_only": False, "tamper": []},
    "deep": {"level": 5, "risk": 3, "threads": 10, "text_only": False, "tamper": []},
    "waf": {
        "level": 4,
        "risk": 2,
        "threads": 4,
        "text_only": True,
        "tamper": ["between", "randomcase", "randomcomments", "space2comment", "charencode"],
    },
}


def _preset_value(config: ScanConfig, key: str):
    return PRESET_DEFAULTS.get(config.preset, PRESET_DEFAULTS["balanced"])[key]


def _append_optional_pair(command: list[str], flag: str, value: object | None) -> None:
    if value is not None and str(value) != "":
        command.extend([flag, str(value)])


def _append_optional_bool(command: list[str], flag: str, enabled: bool) -> None:
    if enabled:
        command.append(flag)


def build_sqlmap_command(config: ScanConfig, sqlmap_script: Path, output_dir: Path) -> list[str]:
    """Build a sqlmap argv list.

    The return value is intentionally a list of arguments, never a shell string.
    This keeps paths with spaces, quotes, and non-ASCII characters safe.
    """

    command = ["python", "-u", sqlmap_script.as_posix()]

    if config.input_type == "raw_request":
        if not config.request_file:
            raise ValueError("raw_request scans require request_file")
        command.extend(["-r", config.request_file])
    else:
        command.extend(["-u", config.target])

    _append_optional_bool(command, "--batch", config.batch)
    _append_optional_bool(command, "--random-agent", config.random_agent)

    level = config.level if config.level is not None else _preset_value(config, "level")
    risk = config.risk if config.risk is not None else _preset_value(config, "risk")
    threads = config.threads if config.threads is not None else _preset_value(config, "threads")
    text_only = config.text_only or bool(_preset_value(config, "text_only"))
    tamper = config.tamper or list(_preset_value(config, "tamper"))

    _append_optional_pair(command, "--level", level)
    _append_optional_pair(command, "--risk", risk)
    _append_optional_pair(command, "--threads", threads)
    _append_optional_bool(command, "--eta", config.eta)
    _append_optional_bool(command, "--parse-errors", config.parse_errors)
    _append_optional_bool(command, "--text-only", text_only)

    _append_optional_pair(command, "--technique", config.technique)
    _append_optional_pair(command, "--dbms", config.dbms)
    _append_optional_pair(command, "-p", config.test_parameter)
    if tamper:
        command.extend(["--tamper", ",".join(tamper)])
    if config.preset == "waf":
        command.append("--skip-waf")

    command.extend(["--output-dir", str(output_dir)])
    command.extend(config.extra_args)
    return command
