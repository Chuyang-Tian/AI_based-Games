"""
判题结果的数据模型（纯 dataclass，不带任何 IO / 状态，JSON 可序列化）。
= 三层嵌套 =
  1. TestCase        ：一道题目的「一个测试点」—— input_data + expected_output，
                       额外属性：case_id（在 DB 里的下标）、time_limit/memory_limit（单测试点可覆盖题目默认）、
                       is_sample（是否是"公开样例"，Step5 日志里只有样例默认可见）。
  2. SingleCaseResult：一次提交里「一个测试点的实际判定结果」—— status（AC/WA/TLE/...）、
                       actual_output / expected_output / input_data（Step5 明细接口按需返回）、
                       time_used / memory_used（答辩时用来画图/统计）、error_message。
  3. JudgeResult     ：一次提交「整体聚合结果」——总 status（所有测试点都 AC 才 AC，否则取最严重的非 AC 状态）、
                       total_cases / passed_cases、total_time / max_memory、
                       case_results（每个测试点 SingleCaseResult 列表，Step5 日志接口返回这个）、
                       compile_message（编译错误时把 g++/javac 的 stderr 放这）、error_message（判题系统错误）。
= 设计要点 =
  所有字段都是基础类型（str/int/float/list），FastAPI 可以直接用 json.dumps 落库到 submissions.details JSON 列，
  不需要额外的 ORM 映射。
"""
from dataclasses import dataclass, field
from typing import List, Optional
from .constants import JudgeStatus


@dataclass
class TestCase:
    input_data: str
    expected_output: str
    case_id: Optional[int] = None
    time_limit: Optional[float] = None
    memory_limit: Optional[int] = None
    is_sample: bool = False
    is_custom: bool = False


@dataclass
class SingleCaseResult:
    case_id: Optional[int]
    status: JudgeStatus
    actual_output: str = ''
    expected_output: str = ''
    input_data: str = ''
    time_used: float = 0.0
    memory_used: float = 0.0
    error_message: str = ''
    is_sample: bool = False
    is_custom: bool = False


@dataclass
class JudgeResult:
    status: JudgeStatus = JudgeStatus.PENDING
    total_cases: int = 0
    passed_cases: int = 0
    total_time: float = 0.0
    max_memory: float = 0.0
    case_results: List[SingleCaseResult] = field(default_factory=list)
    error_message: str = ''
    compile_message: str = ''

    def summary(self) -> dict:
        return {
            'status': self.status.value,
            'description': self.status.description,
            'total_cases': self.total_cases,
            'passed_cases': self.passed_cases,
            'total_time_ms': round(self.total_time * 1000, 2),
            'max_memory_mb': round(self.max_memory, 2),
            'pass_rate': f'{self.passed_cases}/{self.total_cases}' if self.total_cases > 0 else '0/0',
        }
