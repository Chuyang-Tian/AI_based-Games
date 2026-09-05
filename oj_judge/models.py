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
