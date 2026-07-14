import sys
import threading
import time
from pathlib import Path

from backend.sqlmap_gui.engine.subprocess_engine import SubprocessSqlmapEngine

# A child that announces itself then sleeps far longer than the test tolerates,
# so the test only passes if the engine actually terminates it.
LONG_SLEEP = "import time; print('started', flush=True); time.sleep(30)"


def test_cancel_terminates_running_process():
    engine = SubprocessSqlmapEngine()
    cancel = threading.Event()
    lines: list[str] = []
    result: dict[str, int] = {}

    def target():
        result["code"] = engine.run(
            [sys.executable, "-u", "-c", LONG_SLEEP], Path.cwd(), lines.append, cancel
        )

    worker = threading.Thread(target=target)
    worker.start()

    for _ in range(50):
        if lines:
            break
        time.sleep(0.1)
    assert lines and lines[0] == "started"

    cancel.set()
    worker.join(timeout=10)
    assert not worker.is_alive(), "engine did not terminate the child on cancel"


def test_timeout_terminates_running_process():
    engine = SubprocessSqlmapEngine()
    cancel = threading.Event()

    start = time.monotonic()
    engine.run(
        [sys.executable, "-u", "-c", LONG_SLEEP],
        Path.cwd(),
        lambda _line: None,
        cancel,
        timeout=1.0,
    )
    elapsed = time.monotonic() - start
    assert elapsed < 15, "engine ignored the timeout"
