from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_hidden_windows_launcher_runs_start_bat_without_showing_cmd_window():
    launcher = read("SQLmap GUI.vbs")

    assert 'WScript.Shell' in launcher
    assert 'start.bat' in launcher
    assert ', 0, False' in launcher


def test_electron_does_not_expose_external_web_open_handler():
    main = read("apps/desktop/main.cjs")

    assert 'shell.openExternal(url)' not in main
    assert 'setWindowOpenHandler' not in main


def test_renderer_does_not_expose_open_web_version_button():
    app = read("apps/web/src/App.tsx")

    assert 'openWebVersion' not in app
    assert '打开网页版' not in app
    assert 'window.open(webUrl' not in app
