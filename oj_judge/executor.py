import os
import sys
import subprocess
import tempfile
import threading
import time
import shutil
from typing import Optional
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


@dataclass
class PreparedProgram:
    language: str
    workdir: str
    source_file: str
    run_command: str
    tempdir_obj: tempfile.TemporaryDirectory

    def cleanup(self):
        try:
            self.tempdir_obj.cleanup()
        except Exception:
            pass

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
        language='python'
    ) -> ExecutionResult:
        prepared, compile_msg = self.prepare(code, language)
        if compile_msg:
            return ExecutionResult(
                stdout='',
                stderr=compile_msg,
                return_code=1,
                time_used=0.0,
                memory_used=0.0,
                timed_out=False,
                memory_exceeded=False,
            )
        try:
            return self.execute_prepared(prepared, input_data)
        finally:
            prepared.cleanup()

    def prepare(self, code: str, language='python') -> tuple[Optional[PreparedProgram], str]:
        spec = self._normalize_language_spec(language)
        language_name = spec['name']
        tempdir_obj = tempfile.TemporaryDirectory()
        workdir = tempdir_obj.name
        source_base = 'Main' if language_name.startswith('java') else 'solution'
        source_file = os.path.join(workdir, f"{source_base}{spec['file_ext']}")

        try:
            with open(source_file, 'w', encoding='utf-8') as f:
                f.write(code)
        except Exception as e:
            tempdir_obj.cleanup()
            return None, f'写入源代码失败: {e}'

        if language_name in ('python', 'python3'):
            try:
                compile(code, source_file, 'exec')
            except SyntaxError as e:
                tempdir_obj.cleanup()
                return None, f'SyntaxError at line {e.lineno}: {e.msg}\n{e.text}'
            except Exception as e:
                tempdir_obj.cleanup()
                return None, f'Compile check error: {e}'

        binary_name = 'solution_exec.exe' if os.name == 'nt' else 'solution_exec'
        binary_file = os.path.join(workdir, binary_name)
        tokens = self._build_command_tokens(
            source_file=source_file,
            binary_file=binary_file,
            workdir=workdir,
        )

        compile_cmd = spec.get('compile_cmd')
        if compile_cmd:
            compile_result = self._run_compile_command(
                self._format_command(compile_cmd, tokens),
                workdir,
            )
            compile_output = '\n'.join(
                part for part in [compile_result.stdout.strip(), compile_result.stderr.strip()] if part
            ).strip()
            if compile_result.returncode != 0:
                tempdir_obj.cleanup()
                return None, compile_output or f'Compile command failed with exit code {compile_result.returncode}'

        run_command = self._format_command(spec['run_cmd'], tokens)
        return PreparedProgram(
            language=language_name,
            workdir=workdir,
            source_file=source_file,
            run_command=run_command,
            tempdir_obj=tempdir_obj,
        ), ''

    def execute_prepared(self, prepared: PreparedProgram, input_data: str) -> ExecutionResult:
        return self._run_subprocess(prepared.run_command, input_data, prepared.workdir)

    def _normalize_language_spec(self, language) -> dict:
        if isinstance(language, dict):
            raw_name = str(language.get('name') or 'python').strip().lower()
            built_in = self._normalize_language_spec(raw_name)
            if raw_name in ('python', 'python3'):
                return built_in
            compile_cmd = language.get('compile_cmd') if language.get('compile_cmd') else built_in.get('compile_cmd')
            return {
                'name': raw_name,
                'file_ext': str(language.get('file_ext') or built_in.get('file_ext') or '.txt').strip(),
                'compile_cmd': self._normalize_compile_command(compile_cmd),
                'run_cmd': str(language.get('run_cmd') or built_in.get('run_cmd') or '{src}').strip(),
            }
        lang = str(language or 'python').strip().lower()
        if lang in ('python', 'python3'):
            return {
                'name': lang,
                'file_ext': '.py',
                'compile_cmd': None,
                'run_cmd': '{python} -u -B {src}',
            }
        if lang in ('cpp', 'cpp17', 'c++', 'c++17'):
            compiler = self._resolve_cpp_compiler()
            return {
                'name': 'cpp',
                'file_ext': '.cpp',
                'compile_cmd': f'{self._quote(compiler)} -O2 -std=c++17 {{src}} -o {{bin}}' if compiler else 'g++ -O2 -std=c++17 {src} -o {bin}',
                'run_cmd': '{bin}',
            }
        return {
            'name': lang,
            'file_ext': '.txt',
            'compile_cmd': None,
            'run_cmd': '{src}',
        }

    def _build_command_tokens(self, source_file: str, binary_file: str, workdir: str) -> dict:
        return {
            'src': self._quote(source_file),
            'bin': self._quote(binary_file),
            'workdir': self._quote(workdir),
            'python': self._quote(sys.executable),
            'src_name': os.path.basename(source_file),
            'bin_name': os.path.basename(binary_file),
            'main_class': 'Main',
        }

    def _quote(self, value: str) -> str:
        return '"' + str(value).replace('"', '\\"') + '"'

    def _format_command(self, command_template: str, tokens: dict) -> str:
        try:
            return str(command_template).format(**tokens)
        except KeyError as e:
            missing = getattr(e, 'args', ['?'])[0]
            raise RuntimeError(f'语言命令模板缺少占位符: {missing}')

    def _run_compile_command(self, command: str, workdir: str):
        try:
            return subprocess.run(
                command,
                shell=True,
                cwd=workdir,
                env=self._build_subprocess_env(),
                text=True,
                encoding='utf-8',
                errors='replace',
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=max(20.0, self.time_limit * 5),
            )
        except subprocess.TimeoutExpired as e:
            return subprocess.CompletedProcess(
                args=command,
                returncode=124,
                stdout=e.stdout or '',
                stderr=(e.stderr or '') + '\n编译超时',
            )
        except FileNotFoundError as e:
            return subprocess.CompletedProcess(
                args=command,
                returncode=127,
                stdout='',
                stderr=str(e),
            )
        except Exception as e:
            return subprocess.CompletedProcess(
                args=command,
                returncode=1,
                stdout='',
                stderr=f'Compile command error: {e}',
            )

    def _resolve_cpp_compiler(self) -> str:
        candidates = [
            shutil.which('g++.exe'),
            shutil.which('g++'),
            r'C:\msys64\ucrt64\bin\g++.exe',
            r'C:\msys64\mingw64\bin\g++.exe',
        ]
        for candidate in candidates:
            if candidate and os.path.exists(candidate):
                return candidate
        return ''

    def _normalize_compile_command(self, command_template: Optional[str]) -> Optional[str]:
        if not command_template:
            return command_template
        text = str(command_template).strip()
        if text.startswith('g++ '):
            compiler = self._resolve_cpp_compiler()
            if compiler:
                return f'{self._quote(compiler)}{text[3:]}'
        return text

    def _build_subprocess_env(self) -> dict:
        env = os.environ.copy()
        compiler = self._resolve_cpp_compiler()
        if compiler:
            compiler_dir = os.path.dirname(compiler)
            current_path = env.get('PATH') or ''
            parts = current_path.split(os.pathsep) if current_path else []
            if compiler_dir and compiler_dir not in parts:
                env['PATH'] = compiler_dir + os.pathsep + current_path if current_path else compiler_dir
        return env

    def _run_subprocess(
        self,
        command: str,
        input_data: str,
        workdir: str
    ) -> ExecutionResult:
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
                process = subprocess.Popen(
                    command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=workdir,
                    env=self._build_subprocess_env(),
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    bufsize=1,
                    shell=True,
                )
                self._start_memory_monitor(
                    process,
                    memory_peak_container,
                    memory_exceeded_container,
                    stop_monitor,
                )

                out, err = process.communicate(input=input_data)
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
