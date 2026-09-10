"""
判题器的常量与枚举。
= JudgeStatus = 状态枚举（所有 submissions 表的 status 列只允许这里的值）
  AC   Accepted               通过（所有样例都过且 pass=total 才算"用户真正通过"——统计 resolve_count 用这个）
  WA   Wrong Answer           答案错误
  RE   Runtime Error          用户程序运行时抛异常/崩溃/非零退出码
  TLE  Time Limit Exceeded    Step2 核心之一：超时后强制 kill 子进程
  MLE  Memory Limit Exceeded  Step2 核心之二：Windows 下轮询 tasklist RSS，超上限 kill
  CE   Compile Error          C++/Java 编译阶段失败，走不到 run
  SE   System Error           判题系统自己的问题（代码写错、权限不足等）
  PENDING/RUNNING             保留状态，当前同步判题实际用不到，给未来的异步判题队列留位置
= Language = 内置语言枚举（与 languages 表里的 name 对齐）
  command 属性返回默认运行命令；file_ext 对应文件后缀；
  新注册语言（Step2 允许动态注册）不走这个枚举，而是直接存进 languages 表，judge 时按 DB 记录拼命令。
= 默认资源上限 =
  DEFAULT_TIME_LIMIT = 3s（每题可以单独覆盖）；DEFAULT_MEMORY_LIMIT = 256MB。
"""
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
