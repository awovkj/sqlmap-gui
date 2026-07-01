from pathlib import Path

from backend.sqlmap_gui.engine.command_builder import build_sqlmap_command
from backend.sqlmap_gui.schemas.tasks import ScanConfig


def test_builds_url_task_command_with_defaults(tmp_path: Path):
    config = ScanConfig(target="http://127.0.0.1/?id=1", input_type="url")
    command = build_sqlmap_command(config, Path("vendor/sqlmap/sqlmap.py"), tmp_path)

    assert command[:3] == ["python", "-u", "vendor/sqlmap/sqlmap.py"]
    assert command[3:] == [
        "-u", "http://127.0.0.1/?id=1",
        "--batch",
        "--random-agent",
        "--level", "3",
        "--risk", "2",
        "--threads", "6",
        "--eta",
        "--parse-errors",
        "--output-dir", str(tmp_path),
    ]


def test_builds_raw_request_command_with_extra_args(tmp_path: Path):
    request_file = tmp_path / "request.txt"
    config = ScanConfig(
        target="POST /login HTTP/1.1\nHost: example.test\n\na=1",
        input_type="raw_request",
        request_file=str(request_file),
        preset="waf",
        extra_args=["--flush-session", "--dbs"],
    )
    command = build_sqlmap_command(config, Path("vendor/sqlmap/sqlmap.py"), tmp_path / "out")

    assert "-r" in command
    assert str(request_file) in command
    assert "--tamper" in command
    assert command[-2:] == ["--flush-session", "--dbs"]
