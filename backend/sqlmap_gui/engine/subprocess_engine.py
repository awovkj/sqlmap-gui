from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Callable


class SubprocessSqlmapEngine:
    """Runs sqlmap in a child process, streaming stdout line-by-line.

    Cancellation and timeouts terminate the whole process tree so a killed
    sqlmap never leaves orphaned children behind (which plain ``terminate()``
    would on Windows).
    """

    def run(
        self,
        command: list[str],
        cwd: Path,
        on_line: Callable[[str], None],
        cancel_event: threading.Event,
        timeout: float | None = None,
    ) -> int:
        env = {
            **os.environ,
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
            "PYTHONUNBUFFERED": "1",
        }
        kwargs: dict = {
            "cwd": str(cwd),
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "stdin": subprocess.PIPE,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "bufsize": 1,
            "env": env,
        }
        if sys.platform.startswith("win"):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0
            kwargs["startupinfo"] = startupinfo
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        else:
            # Own session/process group so we can signal the whole tree.
            kwargs["start_new_session"] = True

        process = subprocess.Popen(command, **kwargs)
        assert process.stdout is not None
        assert process.stdin is not None

        stop_helpers = threading.Event()

        def auto_answer_stdin() -> None:
            # Fallback for non-batch runs: sqlmap defaults every prompt to "y".
            # Throttled so batch runs (which never read stdin) don't flood the pipe.
            try:
                while process.poll() is None and not stop_helpers.is_set() and not cancel_event.is_set():
                    process.stdin.write("y\n")
                    process.stdin.flush()
                    stop_helpers.wait(0.5)
            except (BrokenPipeError, OSError, ValueError):
                pass

        deadline = time.monotonic() + timeout if timeout else None

        def watch_cancel() -> None:
            # Terminate promptly on cancel/timeout instead of waiting for the
            # next output line to unblock the reader.
            while process.poll() is None and not stop_helpers.is_set():
                if cancel_event.is_set() or (deadline is not None and time.monotonic() > deadline):
                    self._terminate_tree(process)
                    return
                stop_helpers.wait(0.2)

        helpers = [
            threading.Thread(target=auto_answer_stdin, daemon=True),
            threading.Thread(target=watch_cancel, daemon=True),
        ]
        for helper in helpers:
            helper.start()

        try:
            for line in process.stdout:
                on_line(line.rstrip("\n"))
            return process.wait()
        finally:
            stop_helpers.set()
            if process.poll() is None:
                self._terminate_tree(process)
            try:
                process.stdin.close()
            except (BrokenPipeError, OSError, ValueError):
                pass

    @staticmethod
    def _terminate_tree(process: subprocess.Popen) -> None:
        if process.poll() is not None:
            return
        try:
            if sys.platform.startswith("win"):
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            else:
                pgid = os.getpgid(process.pid)
                os.killpg(pgid, signal.SIGTERM)
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(pgid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        except Exception:
            try:
                process.kill()
            except Exception:
                pass
