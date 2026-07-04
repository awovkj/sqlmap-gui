from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Callable


class SubprocessSqlmapEngine:
    def run(
        self,
        command: list[str],
        cwd: Path,
        on_line: Callable[[str], None],
        cancel_event: threading.Event,
    ) -> int:
        env = {
            **os.environ,
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
            "PYTHONUNBUFFERED": "1",
        }
        kwargs = {
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

        process = subprocess.Popen(command, **kwargs)
        assert process.stdout is not None
        assert process.stdin is not None
        
        def auto_answer_stdin():
            try:
                while process.poll() is None:
                    process.stdin.write("y\n")
                    process.stdin.flush()
                    time.sleep(0.1)
            except (BrokenPipeError, OSError):
                pass
        
        stdin_thread = threading.Thread(target=auto_answer_stdin, daemon=True)
        stdin_thread.start()
        
        try:
            for line in process.stdout:
                on_line(line.rstrip("\n"))
                if cancel_event.is_set() and process.poll() is None:
                    process.terminate()
            return process.wait()
        finally:
            if cancel_event.is_set() and process.poll() is None:
                process.terminate()
            try:
                process.stdin.close()
            except (BrokenPipeError, OSError):
                pass
