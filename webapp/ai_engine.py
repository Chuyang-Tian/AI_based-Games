"""
AI Engine 核心模块
==================
- AIEngine: 通过 urllib.request（标准库，不引 SDK）调用 LLM /chat/completions 接口
- 支持 Mock 模式（未配置密钥或用户开启时，返回固定假数据测前端流程）
- count_cost: 按配置的 price_input_per_1k / price_output_per_1k 计算费用
- TaskManager: 全局内存 dict {task_uuid: asyncio.Task}，支持 task.cancel() 真中断
- SSE 事件枚举: start/step/draft/retried/cases/token/complete/cancelled/error
"""

import os
import sys
import re
import json
import time
import uuid
import asyncio
import urllib.request
import urllib.error
import ssl
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from ai_crypto import safe_log, decrypt_api_key, has_crypto
except ImportError:
    def safe_log(x): return str(x)
    def decrypt_api_key(x): return ''
    def has_crypto(): return False


SSE_EVENTS = [
    'start', 'step', 'draft', 'retried', 'cases',
    'token', 'complete', 'cancelled', 'error',
]

MOCK_PROBLEM_JSON = {
    "problem_id_hint": "A100",
    "title": "【AI-Mock】数组排序与去重",
    "description": (
        "小明有一个长度为 N 的整数数组 a_1,a_2,...,a_N。请先将数组从小到大排序，"
        "再输出去重后的结果，每个元素仅保留第一次出现的位置。\n\n"
        "输入格式：\n  第一行一个整数 N (1 ≤ N ≤ 10^5)\n  第二行 N 个整数 a_i (-10^9 ≤ a_i ≤ 10^9)\n\n"
        "输出格式：\n  第一行输出 M 表示去重后的元素个数\n  第二行输出 M 个整数，按升序排列，空格分隔\n\n"
        "提示：期望时间复杂度 O(N log N)，请使用稳定排序。"
    ),
    "tags": ["数组", "排序", "双指针"],
    "difficulty": 2,
    "time_limit": 1.0,
    "memory_limit": 128,
    "compare_mode": "exact",
    "allow_ai_hint": 0,
    "test_cases": [
        {"input": "5\n3 1 4 1 5\n", "output": "4\n1 3 4 5\n", "score": 10, "visibility": "public"},
        {"input": "6\n2 2 2 2 2 2\n", "output": "1\n2\n", "score": 10, "visibility": "public"},
        {"input": "1\n-5\n", "output": "1\n-5\n", "score": 10, "visibility": "hidden"},
    ],
    "solution_python": (
        "import sys\n"
        "def main():\n"
        "    data = sys.stdin.read().split()\n"
        "    if not data:\n"
        "        return\n"
        "    n = int(data[0])\n"
        "    a = list(map(int, data[1:1+n]))\n"
        "    a.sort()\n"
        "    res = []\n"
        "    prev = None\n"
        "    for x in a:\n"
        "        if x != prev:\n"
        "            res.append(str(x))\n"
        "            prev = x\n"
        "    print(len(res))\n"
        "    print(' '.join(res))\n"
        "main()\n"
    ),
}


@dataclass
class ModelConfig:
    provider: str = 'openai'
    base_url: str = 'https://api.openai.com/v1'
    model_name: str = 'gpt-4o-mini'
    api_key_plain: str = ''
    price_input_per_1k: float = 0.00015
    price_output_per_1k: float = 0.0006
    currency: str = 'CNY'
    mock_mode: bool = False

    @property
    def is_usable(self) -> bool:
        if self.mock_mode:
            return True
        return bool(self.api_key_plain and self.base_url and self.model_name)


@dataclass
class ChatResult:
    ok: bool = False
    content: str = ''
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    error: str = ''
    raw: Dict[str, Any] = field(default_factory=dict)


class AIEngine:
    """
    LLM 调用封装。
    - 标准库 urllib.request，不引任何 SDK
    - 超时 120s；失败自动重试 1 次；全链路 safe_log 打码
    """

    DEFAULT_TIMEOUT = 120
    MAX_RETRY = 1

    def __init__(self, config: Optional[ModelConfig] = None):
        self.config = config or ModelConfig()

    def _headers(self) -> dict:
        hdrs = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'OJ-Debug-Platform/1.0 AI-Engine',
        }
        if self.config.api_key_plain:
            hdrs['Authorization'] = f'Bearer {self.config.api_key_plain}'
            if self.config.provider == 'anthropic':
                hdrs['x-api-key'] = self.config.api_key_plain
                hdrs['anthropic-version'] = '2023-06-01'
        return hdrs

    def _endpoint(self) -> str:
        base = self.config.base_url.rstrip('/')
        if self.config.provider == 'anthropic':
            return f'{base}/v1/messages'
        return f'{base}/chat/completions'

    def count_cost(self, input_tokens: int, output_tokens: int) -> float:
        c = self.config
        return round(
            (input_tokens / 1000.0) * c.price_input_per_1k +
            (output_tokens / 1000.0) * c.price_output_per_1k,
            6,
        )

    def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_json: bool = False,
        timeout: Optional[int] = None,
    ) -> ChatResult:
        """
        同步调用 LLM chat（async 路由里请用 asyncio.to_thread 包装）。
        未配置密钥 → 走 Mock 模式，content 以固定 JSON 返回。
        """
        cfg = self.config
        if cfg.mock_mode or not cfg.is_usable:
            t0 = time.perf_counter()
            time.sleep(0.15)
            content = MOCK_PROBLEM_JSON if response_json else 'pong'
            if not isinstance(content, str):
                content = json.dumps(content, ensure_ascii=False, indent=2)
            return ChatResult(
                ok=True, content=content,
                input_tokens=sum(len(m.get('content', '')) for m in messages) // 4 + 50,
                output_tokens=len(content) // 4 + 30,
                latency_ms=int((time.perf_counter() - t0) * 1000),
            )
        t0 = time.perf_counter()
        last_err = ''
        for attempt in range(self.MAX_RETRY + 1):
            try:
                body = {
                    'model': cfg.model_name,
                    'messages': messages,
                    'temperature': temperature,
                    'max_tokens': max_tokens,
                }
                if response_json:
                    if cfg.provider != 'anthropic':
                        body['response_format'] = {'type': 'json_object'}
                raw_body = json.dumps(body, ensure_ascii=False).encode('utf-8')
                req = urllib.request.Request(
                    self._endpoint(),
                    data=raw_body,
                    headers=self._headers(),
                    method='POST',
                )
                ctx = ssl.create_default_context()
                with urllib.request.urlopen(
                    req,
                    timeout=timeout or self.DEFAULT_TIMEOUT,
                    context=ctx,
                ) as resp:
                    raw = resp.read().decode('utf-8', errors='replace')
                data = json.loads(raw)
                itok = 0
                otok = 0
                usage = data.get('usage') or {}
                if cfg.provider == 'anthropic':
                    itok = usage.get('input_tokens', 0)
                    otok = usage.get('output_tokens', 0)
                    content_parts = data.get('content', [])
                    text = ''.join(
                        p.get('text', '') for p in content_parts if p.get('type') == 'text'
                    )
                else:
                    itok = usage.get('prompt_tokens', 0)
                    otok = usage.get('completion_tokens', 0)
                    choices = data.get('choices', [])
                    text = choices[0].get('message', {}).get('content', '') if choices else ''
                return ChatResult(
                    ok=True,
                    content=text.strip(),
                    input_tokens=int(itok),
                    output_tokens=int(otok),
                    latency_ms=int((time.perf_counter() - t0) * 1000),
                    raw=data,
                )
            except urllib.error.HTTPError as e:
                try:
                    body_txt = e.read().decode('utf-8', errors='replace')
                except Exception:
                    body_txt = ''
                last_err = f'HTTP {e.code}: {safe_log(body_txt or e.reason)}'
            except urllib.error.URLError as e:
                last_err = f'URL Error: {safe_log(e.reason)}'
            except Exception as e:
                last_err = f'Exception: {safe_log(e)}'
            if attempt < self.MAX_RETRY:
                time.sleep(0.6 * (attempt + 1))
        return ChatResult(ok=False, error=last_err, latency_ms=int((time.perf_counter() - t0) * 1000))


class TaskManager:
    """
    全局内存任务管理器：{task_uuid: asyncio.Task}
    - cancel(task_uuid): 真正调用 task.cancel() 中断协程
    - 未完成任务在进程退出时无需清理（内存即丢，符合NFR2）
    """

    def __init__(self):
        self._tasks: Dict[str, asyncio.Task] = {}
        self._meta: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock() if sys.version_info >= (3, 10) else None

    def _get_lock(self):
        if self._lock is None:
            class _Dummy:
                async def __aenter__(self): return None
                async def __aexit__(self, *a): return None
            self._lock = _Dummy()
        return self._lock

    async def register(self, task: asyncio.Task, *, task_uuid: Optional[str] = None,
                       user_id: str = '', task_type: str = 'other') -> str:
        if task_uuid is None:
            task_uuid = uuid.uuid4().hex
        lock = self._get_lock()
        async with lock:
            self._tasks[task_uuid] = task
            self._meta[task_uuid] = {
                'user_id': str(user_id),
                'task_type': task_type,
                'started_at': int(time.time() * 1000),
                'status': 'running',
            }
        return task_uuid

    async def cancel(self, task_uuid: str, *, by_user: bool = True) -> bool:
        lock = self._get_lock()
        async with lock:
            t = self._tasks.get(task_uuid)
            meta = self._meta.get(task_uuid, {})
            if t is None:
                return False
            if not t.done():
                t.cancel()
            meta['status'] = 'cancelled'
            meta['cancelled_by_user'] = by_user
            meta['cancelled_at'] = int(time.time() * 1000)
            return True

    async def get_meta(self, task_uuid: str) -> Dict[str, Any]:
        lock = self._get_lock()
        async with lock:
            return dict(self._meta.get(task_uuid, {}))

    async def update_meta(self, task_uuid: str, **kwargs) -> None:
        lock = self._get_lock()
        async with lock:
            if task_uuid in self._meta:
                self._meta[task_uuid].update(kwargs)

    async def cleanup_done(self, max_age_ms: int = 3600_000) -> int:
        now = int(time.time() * 1000)
        lock = self._get_lock()
        n = 0
        async with lock:
            for k in list(self._tasks.keys()):
                t = self._tasks[k]
                if t.done():
                    started = self._meta.get(k, {}).get('started_at', 0)
                    if now - started > max_age_ms:
                        self._tasks.pop(k, None)
                        self._meta.pop(k, None)
                        n += 1
        return n


GLOBAL_TASK_MANAGER = TaskManager()


def format_sse(event: str, data: Any) -> bytes:
    """
    按 SSE 协议格式序列化事件：
      event: xxx\n
      data: json_line\n\n
    """
    if not isinstance(data, str):
        try:
            data_str = json.dumps(data, ensure_ascii=False)
        except Exception:
            data_str = str(data)
    else:
        data_str = data
    lines = [f'event: {event}']
    for line in data_str.splitlines() or ['']:
        lines.append(f'data: {line}')
    return ('\n'.join(lines) + '\n\n').encode('utf-8')
