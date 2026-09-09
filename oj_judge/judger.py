from typing import List, Optional, Callable, Any
from .constants import (
    JudgeStatus,
    Language,
    DEFAULT_TIME_LIMIT,
    DEFAULT_MEMORY_LIMIT,
)
from .models import TestCase, JudgeResult, SingleCaseResult
from .executor import CodeExecutor, ExecutionResult, PreparedProgram
from .comparator import OutputComparator


class Judger:
    def __init__(
        self,
        default_time_limit: float = DEFAULT_TIME_LIMIT,
        default_memory_limit: int = DEFAULT_MEMORY_LIMIT,
        compare_mode: str = 'exact',
        float_precision: float = 1e-6,
        on_case_start: Optional[Callable[[int, TestCase], None]] = None,
        on_case_end: Optional[Callable[[int, TestCase, SingleCaseResult], None]] = None,
    ):
        self.default_time_limit = default_time_limit
        self.default_memory_limit = default_memory_limit
        self.compare_mode = compare_mode
        self.float_precision = float_precision
        self.on_case_start = on_case_start
        self.on_case_end = on_case_end

    def judge(
        self,
        code: str,
        test_cases: List[TestCase],
        language: Any = Language.PYTHON,
    ) -> JudgeResult:
        result = JudgeResult(
            status=JudgeStatus.PENDING,
            total_cases=len(test_cases),
            case_results=[],
        )

        compile_executor = CodeExecutor(
            time_limit=max(self.default_time_limit, 5.0),
            memory_limit=max(self.default_memory_limit, 256),
        )
        prepared_program, compile_msg = compile_executor.prepare(code, self._normalize_language(language))
        if compile_msg:
            result.status = JudgeStatus.CE
            result.compile_message = compile_msg
            result.error_message = '编译/语法错误'
            for i, tc in enumerate(test_cases):
                result.case_results.append(SingleCaseResult(
                    case_id=tc.case_id if tc.case_id is not None else i,
                    status=JudgeStatus.CE,
                    input_data=tc.input_data,
                    expected_output=tc.expected_output,
                    error_message=compile_msg,
                    is_sample=tc.is_sample,
                    is_custom=tc.is_custom,
                ))
            return result

        result.status = JudgeStatus.RUNNING
        passed_count = 0
        total_time = 0.0
        max_memory = 0.0

        try:
            for i, tc in enumerate(test_cases):
                if self.on_case_start:
                    self.on_case_start(i, tc)

                case_result = self._judge_single_case(prepared_program, tc, i)
                case_result.is_sample = tc.is_sample
                case_result.is_custom = tc.is_custom
                result.case_results.append(case_result)

                total_time += case_result.time_used
                if case_result.memory_used > max_memory:
                    max_memory = case_result.memory_used

                if case_result.status == JudgeStatus.AC:
                    passed_count += 1

                if self.on_case_end:
                    self.on_case_end(i, tc, case_result)
        finally:
            if prepared_program is not None:
                prepared_program.cleanup()

        result.passed_cases = passed_count
        result.total_time = total_time
        result.max_memory = max_memory

        if passed_count == len(test_cases) and test_cases:
            result.status = JudgeStatus.AC
        else:
            non_ac = [cr for cr in result.case_results if cr.status != JudgeStatus.AC]
            if non_ac:
                priority = [JudgeStatus.RE, JudgeStatus.TLE, JudgeStatus.MLE, JudgeStatus.SE, JudgeStatus.CE, JudgeStatus.WA]
                for s in priority:
                    if any(cr.status == s for cr in non_ac):
                        result.status = s
                        break
                else:
                    result.status = non_ac[0].status
            else:
                result.status = JudgeStatus.WA

        return result

    def _judge_single_case(
        self,
        prepared_program: PreparedProgram,
        tc: TestCase,
        index: int,
    ) -> SingleCaseResult:
        time_limit = tc.time_limit if tc.time_limit is not None else self.default_time_limit
        memory_limit = tc.memory_limit if tc.memory_limit is not None else self.default_memory_limit

        executor = CodeExecutor(time_limit=time_limit, memory_limit=memory_limit)

        try:
            exec_result: ExecutionResult = executor.execute_prepared(
                prepared_program,
                input_data=tc.input_data,
            )
        except Exception as e:
            return SingleCaseResult(
                case_id=tc.case_id if tc.case_id is not None else index,
                status=JudgeStatus.SE,
                input_data=tc.input_data,
                expected_output=tc.expected_output,
                error_message=f'System Error: {e}',
                is_sample=tc.is_sample,
            )

        case_id = tc.case_id if tc.case_id is not None else index

        if exec_result.memory_exceeded:
            return SingleCaseResult(
                case_id=case_id,
                status=JudgeStatus.MLE,
                input_data=tc.input_data,
                expected_output=tc.expected_output,
                actual_output=exec_result.stdout,
                time_used=exec_result.time_used,
                memory_used=exec_result.memory_used,
                error_message=f'内存超限 (使用 {exec_result.memory_used:.1f}MB / 限制 {memory_limit}MB)',
                is_sample=tc.is_sample,
            )

        if exec_result.timed_out:
            return SingleCaseResult(
                case_id=case_id,
                status=JudgeStatus.TLE,
                input_data=tc.input_data,
                expected_output=tc.expected_output,
                actual_output=exec_result.stdout,
                time_used=time_limit,
                memory_used=exec_result.memory_used,
                error_message=f'运行超时 (超过 {time_limit}s)',
                is_sample=tc.is_sample,
            )

        if exec_result.return_code != 0 or exec_result.stderr:
            if 'MemoryError' in exec_result.stderr:
                return SingleCaseResult(
                    case_id=case_id,
                    status=JudgeStatus.MLE,
                    input_data=tc.input_data,
                    expected_output=tc.expected_output,
                    actual_output=exec_result.stdout,
                    time_used=exec_result.time_used,
                    memory_used=exec_result.memory_used,
                    error_message=exec_result.stderr.strip(),
                    is_sample=tc.is_sample,
                )
            return SingleCaseResult(
                case_id=case_id,
                status=JudgeStatus.RE,
                input_data=tc.input_data,
                expected_output=tc.expected_output,
                actual_output=exec_result.stdout,
                time_used=exec_result.time_used,
                memory_used=exec_result.memory_used,
                error_message=exec_result.stderr.strip() if exec_result.stderr else f'Exit code: {exec_result.return_code}',
                is_sample=tc.is_sample,
            )

        if self._compare_output(exec_result.stdout, tc.expected_output):
            return SingleCaseResult(
                case_id=case_id,
                status=JudgeStatus.AC,
                input_data=tc.input_data,
                expected_output=tc.expected_output,
                actual_output=exec_result.stdout,
                time_used=exec_result.time_used,
                memory_used=exec_result.memory_used,
                is_sample=tc.is_sample,
            )
        else:
            diff_a, diff_e = OutputComparator.diff(exec_result.stdout, tc.expected_output)
            return SingleCaseResult(
                case_id=case_id,
                status=JudgeStatus.WA,
                input_data=tc.input_data,
                expected_output=tc.expected_output,
                actual_output=exec_result.stdout,
                time_used=exec_result.time_used,
                memory_used=exec_result.memory_used,
                error_message=f'输出不匹配\n---你的输出---\n{diff_a}\n---期望输出---\n{diff_e}',
                is_sample=tc.is_sample,
            )

    def _normalize_language(self, language: Any):
        if isinstance(language, dict):
            return language
        if isinstance(language, Language):
            return language.value
        return str(language or 'python').strip().lower()

    def _compare_output(self, actual: str, expected: str) -> bool:
        if self.compare_mode == 'tokens':
            return OutputComparator.compare_tokens(actual, expected)
        elif self.compare_mode == 'float':
            return OutputComparator.compare_floats(actual, expected, self.float_precision)
        else:
            return OutputComparator.compare_exact(actual, expected)
