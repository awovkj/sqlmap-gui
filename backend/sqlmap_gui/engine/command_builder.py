from __future__ import annotations

from pathlib import Path

from backend.sqlmap_gui.schemas.tasks import ScanConfig


PRESET_DEFAULTS: dict[str, dict[str, object]] = {
    "balanced": {
        "level": 3, "risk": 2, "threads": 6,
        "text_only": False, "tamper": [],
    },
    "deep": {
        "level": 5, "risk": 3, "threads": 10,
        "text_only": False, "tamper": [],
    },
    "waf": {
        "level": 4, "risk": 2, "threads": 4,
        "text_only": True,
        "tamper": ["between", "randomcase", "randomcomments", "space2comment", "charencode"],
    },
    "enum_structure": {
        "level": 3, "risk": 2, "threads": 6,
        "text_only": False, "tamper": [],
    },
    "data_export": {
        "level": 3, "risk": 2, "threads": 6,
        "text_only": False, "tamper": [],
    },
}


def _preset_value(config: ScanConfig, key: str) -> object:
    return PRESET_DEFAULTS.get(config.preset, PRESET_DEFAULTS["balanced"]).get(key)


def _opt(command: list[str], flag: str, value: object | None) -> None:
    if value is not None and str(value).strip() != "":
        command.extend([flag, str(value)])


def _bool(command: list[str], flag: str, enabled: bool) -> None:
    if enabled:
        command.append(flag)


def build_sqlmap_command(config: ScanConfig, sqlmap_script: Path, output_dir: Path) -> list[str]:
    """Build a sqlmap argv list.

    The return value is intentionally a list of arguments, never a shell string.
    This keeps paths with spaces, quotes, and non-ASCII characters safe.
    """

    command: list[str] = ["python", "-u", sqlmap_script.as_posix()]

    if config.input_type == "raw_request":
        if not config.request_file:
            raise ValueError("raw_request scans require request_file")
        command.extend(["-r", config.request_file])
    else:
        command.extend(["-u", config.target])

    _bool(command, "--batch", config.batch)
    _bool(command, "--random-agent", config.random_agent)

    level = config.level if config.level is not None else _preset_value(config, "level")
    risk = config.risk if config.risk is not None else _preset_value(config, "risk")
    threads = config.threads if config.threads is not None else _preset_value(config, "threads")

    _opt(command, "--level", level)
    _opt(command, "--risk", risk)
    _opt(command, "--threads", threads)
    _bool(command, "--eta", config.eta)
    _bool(command, "--parse-errors", config.parse_errors)

    _opt(command, "--technique", config.technique)
    _opt(command, "--dbms", config.dbms)
    _opt(command, "-p", config.test_parameter)
    _opt(command, "--skip", config.skip_parameter)
    _opt(command, "--param-exclude", config.param_exclude)
    _opt(command, "--param-filter", config.param_filter)
    _opt(command, "-D", config.custom_db)
    _opt(command, "-T", config.custom_table)
    _opt(command, "-C", config.custom_column)

    _opt(command, "--prefix", config.prefix)
    _opt(command, "--suffix", config.suffix)
    _opt(command, "--time-sec", config.time_sec)
    _opt(command, "--union-cols", config.union_cols)
    _opt(command, "--union-char", config.union_char)
    _opt(command, "--union-from", config.union_from)
    _opt(command, "--union-values", config.union_values)

    _opt(command, "--string", config.string)
    _opt(command, "--not-string", config.not_string)
    _opt(command, "--regexp", config.regexp)
    _opt(command, "--code", config.code)
    _opt(command, "--test-filter", config.test_filter)
    _opt(command, "--test-skip", config.test_skip)

    tamper = config.tamper or list(_preset_value(config, "tamper") or [])
    if tamper:
        command.extend(["--tamper", ",".join(tamper)])

    text_only = config.text_only or bool(_preset_value(config, "text_only"))
    _bool(command, "--force-ssl", config.force_ssl)
    _bool(command, "--text-only", text_only)
    _bool(command, "--skip-waf", config.skip_waf)
    _bool(command, "--skip-static", config.skip_static)
    _bool(command, "--smart", config.smart)
    _bool(command, "--titles", config.titles)
    _bool(command, "--skip-heuristics", config.skip_heuristics)
    _bool(command, "--flush-session", config.flush_session)
    _bool(command, "--no-cast", config.no_cast)
    _bool(command, "--no-escape", config.no_escape)
    _bool(command, "--invalid-bignum", config.invalid_bignum)
    _bool(command, "--invalid-logical", config.invalid_logical)
    _bool(command, "--invalid-string", config.invalid_string)

    _bool(command, "--current-db", config.current_db)
    _bool(command, "--current-user", config.current_user)
    _bool(command, "--is-dba", config.is_dba)
    _bool(command, "--dbs", config.dbs)
    _bool(command, "--tables", config.tables)
    _bool(command, "--columns", config.columns)
    _bool(command, "--dump", config.dump)
    _bool(command, "--dump-all", config.dump_all)

    command.extend(["--output-dir", str(output_dir)])
    _opt(command, "--proxy", config.proxy)
    command.extend(config.extra_args)

    return command
