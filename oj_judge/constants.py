from enum import Enum


class JudgeStatus(str, Enum):
    AC = 'AC'
    WA = 'WA'
    RE = 'RE'
    TLE = 'TLE'
    MLE = 'MLE'
    CE = 'CE'
    SE = 'SE'
    PENDING = 'PENDING'
    RUNNING = 'RUNNING'

    @property
    def description(self) -> str:
        descriptions = {
            JudgeStatus.AC: 'Accepted - 通过',
            JudgeStatus.WA: 'Wrong Answer - 答案错误',
            JudgeStatus.RE: 'Runtime Error - 运行时错误',
            JudgeStatus.TLE: 'Time Limit Exceeded - 超时',
            JudgeStatus.MLE: 'Memory Limit Exceeded - 超出内存限制',
            JudgeStatus.CE: 'Compile Error - 编译错误',
            JudgeStatus.SE: 'System Error - 系统错误',
            JudgeStatus.PENDING: 'Pending - 等待判题',
            JudgeStatus.RUNNING: 'Running - 判题中',
        }
        return descriptions.get(self, 'Unknown')


class Language(str, Enum):
    PYTHON = 'python'
    PYTHON3 = 'python3'

    @property
    def command(self) -> str:
        commands = {
            Language.PYTHON: 'python',
            Language.PYTHON3: 'python',
        }
        return commands.get(self, 'python')

    @property
    def extension(self) -> str:
        return '.py'


DEFAULT_TIME_LIMIT = 1.0
DEFAULT_MEMORY_LIMIT = 128
