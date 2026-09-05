import os
import sys
import subprocess
import tempfile
import threading
import time
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    return_code: int
    time_used: float
    memory_used: float
    timed_out: bool
    memory_exceeded: bool


class CodeExecutor:
    def __init__(self, time_limit: float = 1.0, memory_limit: int = 128):
        self.time_limit = time_limit
        self.memory_limit = memory_limit
        self._psutil_available = False
        try:
            import psutil
            self._psutil = psutil
            self._psutil_available = True
        except ImportError:
            self._psutil = None

    def execute(
        self,
        code: str,
        input_data: str,
        language: str = 'python'
    ) -> ExecutionResult:
        with tempfile.TemporaryDirectory() as tmpdir:
            code_file = os.path.join(tmpdir, f'solution{self._get_extension(language)}')
            with open(code_file, 'w', encoding='utf-8') as f:
                f.write(code)

            input_file = os.path.join(tmpdir, 'stdin.txt')
            with open(input_file, 'w', encoding='utf-8') as f:
                f.write(input_data)

            return self._run_subprocess(code_file, input_file, tmpdir)

    def _get_extension(self, language: str) -> str:
        return '.py'

    def _run_subprocess(
        self,
        code_file: str,
        input_file: str,
        workdir: str
    ) -> ExecutionResult:
        cmd = [sys.executable, '-u', '-B', code_file]

        stdout_container: list[str] = ['']
        stderr_container: list[str] = ['']
        memory_peak_container: list[float] = [0.0]
        memory_exceeded_container: list[bool] = [False]
        stop_monitor = threading.Event()
        start_time = time.perf_counter()
        process: Optional[subprocess.Popen] = None

        def target():
            nonlocal process
            try:
                with open(input_file, 'r', encoding='utf-8') as stdin_f:
                    process = subprocess.Popen(
                        cmd,
                        stdin=stdin_f,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        cwd=workdir,
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        bufsize=1,
                    )

                self._start_memory_monitor(
                    process,
                    memory_peak_container,
                    memory_exceeded_container,
                    stop_monitor,
                )

                out, err = process.communicate()
                stdout_container[0] = out or ''
                stderr_container[0] = err or ''
            except Exception as e:
                stderr_container[0] = f'SystemError: {e}'

        exec_thread = threading.Thread(target=target)
        exec_thread.daemon = True
        exec_thread.start()
        exec_thread.join(timeout=self.time_limit)

        timed_out = False
        if exec_thread.is_alive():
            timed_out = True
            stop_monitor.set()
            if process and process.poll() is None:
                try:
                    process.terminate()
                    try:
                        process.wait(timeout=0.5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                except Exception:
                    pass
            exec_thread.join(timeout=0.5)

        stop_monitor.set()
        time_used = time.perf_counter() - start_time
        return_code = process.returncode if (process and process.returncode is not None) else -1

        memory_peak = memory_peak_container[0]
        memory_exceeded = memory_exceeded_container[0] or memory_peak > self.memory_limit

        return ExecutionResult(
            stdout=stdout_container[0],
            stderr=stderr_container[0],
            return_code=return_code,
            time_used=min(time_used, self.time_limit + 0.1),
            memory_used=memory_peak,
            timed_out=timed_out and not memory_exceeded,
            memory_exceeded=memory_exceeded,
        )

    def _start_memory_monitor(
        self,
        process: subprocess.Popen,
        memory_peak_container: list,
        memory_exceeded_container: list,
        stop_event: threading.Event,
    ):
        if not self._psutil_available:
            return

        def monitor():
            try:
                proc = self._psutil.Process(process.pid)
            except (self._psutil.NoSuchProcess, self._psutil.AccessDenied, Exception):
                return

            while not stop_event.is_set() and process.poll() is None:
                try:
                    current_mem = 0.0
                    try:
                        children = proc.children(recursive=True)
                        all_procs = [proc] + children
                        for p in all_procs:
                            try:
                                if p.is_running():
                                    current_mem += p.memory_info().rss / (1024 * 1024)
                            except (self._psutil.NoSuchProcess, self._psutil.AccessDenied):
                                pass
                    except Exception:
                        try:
                            if proc.is_running():
                                current_mem = proc.memory_info().rss / (1024 * 1024)
                        except Exception:
                            pass

                    if current_mem > memory_peak_container[0]:
                        memory_peak_container[0] = current_mem

                    if current_mem > self.memory_limit and not memory_exceeded_container[0]:
                        memory_exceeded_container[0] = True
                        try:
                            parent = self._psutil.Process(process.pid)
                            for child in parent.children(recursive=True):
                                try:
                                    child.kill()
                                except Exception:
                                    pass
                            parent.kill()
                        except Exception:
                            pass
                        break
                except Exception:
                    pass

                stop_event.wait(timeout=0.02)

        t = threading.Thread(target=monitor, daemon=True)
        t.start()
