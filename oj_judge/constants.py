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
    CPP = 'cpp'
    CPP17 = 'cpp17'

    @property
    def command(self) -> str:
        commands = {
            Language.PYTHON: 'python',
            Language.PYTHON3: 'python',
            Language.CPP: 'g++',
            Language.CPP17: 'g++',
        }
        return commands.get(self, 'python')

    @property
    def extension(self) -> str:
        extensions = {
            Language.PYTHON: '.py',
            Language.PYTHON3: '.py',
            Language.CPP: '.cpp',
            Language.CPP17: '.cpp',
        }
        return extensions.get(self, '.py')


DEFAULT_TIME_LIMIT = 1.0
DEFAULT_MEMORY_LIMIT = 128
