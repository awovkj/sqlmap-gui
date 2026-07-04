from pathlib import Path

from backend.sqlmap_gui.core.artifacts import ArtifactsManager
from backend.sqlmap_gui.reports.service import ReportService


def parse(lines: list[str], tmp_path: Path) -> dict[str, list[str]]:
    service = ReportService(ArtifactsManager(tmp_path / "artifacts"))
    return service._parse_injection_results(lines)


def test_parse_database_and_current_identity_results(tmp_path: Path):
    results = parse(
        [
            "[INFO] fetching database names",
            "available databases [2]",
            "[*] information_schema",
            "[*] security",
            "[INFO] fetched data logged to text files under output directory",
            "current database: 'security'",
            "current user: 'root@localhost'",
        ],
        tmp_path,
    )

    assert results["databases"] == ["information_schema", "security"]
    assert results["current_db"] == ["security"]
    assert results["current_user"] == ["root@localhost"]


def test_parse_table_and_column_ascii_sections(tmp_path: Path):
    results = parse(
        [
            "[INFO] fetching tables for database: 'security'",
            "+-------+",
            "| users |",
            "| emails |",
            "+-------+",
            "Database: security",
            "Table: users",
            "[3 columns]",
            "+----------+-------------+",
            "| Column   | Type        |",
            "+----------+-------------+",
            "| id       | int(11)     |",
            "| username | varchar(20) |",
            "| password | varchar(20) |",
            "+----------+-------------+",
        ],
        tmp_path,
    )

    assert results["tables"] == ["users", "emails"]
    assert results["columns"] == ["id", "username", "password"]


def test_database_parser_does_not_treat_sqlmap_lifecycle_lines_as_results(tmp_path: Path):
    results = parse(
        [
            "available databases [1]:",
            "[*] security",
            "",
            "[*] ending @ 22:26:35 /2026-07-03/",
        ],
        tmp_path,
    )

    assert results["databases"] == ["security"]
