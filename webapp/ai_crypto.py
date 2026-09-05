"""
AI 加密工具模块
==============
- Fernet 对称加密（AES-128-CBC + HMAC）：加密存储 LLM API Key
- 密钥来源：优先环境变量 OJ_AI_ENC_KEY，否则写入 %USERPROFILE%/.trae/oj_ai_key.json
- safe_log: 全局正则打码 sk- / gsk- 开头的 20+ 字符密钥

【注意】本模块 try/except 优雅降级：如果用户还没 pip install cryptography，
则返回 None 并打印 WARNING，其他模块拿到 None 时走 Mock 模式（不影响其他功能）。
用户手动 pip install cryptography 后重启 uvicorn 自动启用真加密。
"""

import os
import re
import sys
import json
import base64
import warnings
from pathlib import Path
from typing import Optional, Union

try:
    from cryptography.fernet import Fernet, InvalidToken
    _HAS_CRYPTO = True
except ImportError:
    _HAS_CRYPTO = False
    Fernet = None
    InvalidToken = Exception

_KEY_RE = re.compile(r'(sk-|gsk-|sk-[a-zA-Z0-9]{20,}|gsk-[a-zA-Z0-9]{20,})', re.IGNORECASE)
_LONG_KEY_RE = re.compile(r'[A-Za-z0-9_\-]{32,}')

_CACHED_FERNET = None


def has_crypto() -> bool:
    return _HAS_CRYPTO


def get_key_path() -> str:
    home = Path.home()
    trae_dir = home / '.trae'
    trae_dir.mkdir(parents=True, exist_ok=True)
    return str(trae_dir / 'oj_ai_key.json')


def _gen_new_key_bytes() -> bytes:
    if not _HAS_CRYPTO:
        return base64.urlsafe_b64encode(b'oj_mock_key_pad_pad_pad_pad_pad_pad_pad=')
    return Fernet.generate_key()


def get_fernet_key() -> Optional[bytes]:
    """
    按优先级返回 Fernet 密钥 bytes：
    1. 环境变量 OJ_AI_ENC_KEY
    2. %USERPROFILE%/.trae/oj_ai_key.json（不存在自动生成）
    未安装 cryptography 时返回 None
    """
    global _CACHED_FERNET
    if _CACHED_FERNET is not None:
        return _CACHED_FERNET
    if not _HAS_CRYPTO:
        warnings.warn(
            "[AI Crypto] 未安装 cryptography 包，密钥加密功能降级为Mock。"
            "请手动执行: pip install cryptography，然后重启 uvicorn。",
            stacklevel=2
        )
        return None
    env_key = os.environ.get('OJ_AI_ENC_KEY', '').strip()
    if env_key:
        try:
            if not env_key.endswith('='):
                env_bytes = env_key.encode('utf-8')
                if len(env_bytes) != 32:
                    env_bytes = base64.urlsafe_b64decode(env_key + '=' * (-len(env_key) % 4))
                else:
                    env_bytes = base64.urlsafe_b64encode(env_bytes)
            else:
                env_bytes = env_key.encode('utf-8')
            Fernet(env_bytes)
            _CACHED_FERNET = env_bytes
            return _CACHED_FERNET
        except Exception:
            pass
    key_path = get_key_path()
    try:
        if os.path.exists(key_path):
            with open(key_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            k = data.get('fernet_key_b64', '').encode('utf-8')
            Fernet(k)
            _CACHED_FERNET = k
            return _CACHED_FERNET
    except Exception:
        pass
    new_key = _gen_new_key_bytes()
    try:
        with open(key_path, 'w', encoding='utf-8') as f:
            json.dump({
                'fernet_key_b64': new_key.decode('utf-8'),
                'created_at': __import__('datetime').datetime.now().isoformat(),
                'warn': '生产环境请 export OJ_AI_ENC_KEY=<以上fernet_key_b64>，勿把此json提交到Git',
            }, f, ensure_ascii=False, indent=2)
        os.chmod(key_path, 0o600)
    except Exception:
        pass
    if not os.environ.get('OJ_AI_ENC_KEY'):
        warnings.warn(
            "[AI Crypto] 警告：当前 Fernet 密钥从 ~/.trae/oj_ai_key.json 读取（开发模式）。"
            "生产环境请手动 export OJ_AI_ENC_KEY=<key_b64> 以获得更高安全性。",
            stacklevel=2
        )
    _CACHED_FERNET = new_key
    return _CACHED_FERNET


def _get_fernet():
    if not _HAS_CRYPTO:
        return None
    k = get_fernet_key()
    if k is None:
        return None
    try:
        return Fernet(k)
    except Exception:
        return None


def encrypt_api_key(plain: str) -> bytes:
    """
    加密 API Key 明文，返回 BLOB bytes。
    未安装 cryptography 时返回 base64(plain) 伪加密（仅Mock用，生产需装包）。
    """
    if not isinstance(plain, str):
        plain = '' if plain is None else str(plain)
    f = _get_fernet()
    if f is not None:
        return f.encrypt(plain.encode('utf-8'))
    return b'MOCK:' + base64.urlsafe_b64encode(plain.encode('utf-8'))


def decrypt_api_key(cipher: Union[bytes, bytearray, memoryview, None]) -> str:
    """
    解密 BLOB 为明文。cipher 为空时返回 ''
    """
    if cipher is None:
        return ''
    if isinstance(cipher, (bytearray, memoryview)):
        cipher = bytes(cipher)
    if isinstance(cipher, str):
        cipher = cipher.encode('utf-8', errors='ignore')
    if cipher.startswith(b'MOCK:'):
        try:
            return base64.urlsafe_b64decode(cipher[5:]).decode('utf-8')
        except Exception:
            return ''
    f = _get_fernet()
    if f is None:
        return ''
    try:
        return f.decrypt(cipher).decode('utf-8')
    except InvalidToken:
        warnings.warn("[AI Crypto] 解密失败：InvalidToken，密钥可能变更。请在管理员AI配置页重新填写API Key。", stacklevel=2)
        return ''
    except Exception:
        return ''


def safe_log(obj) -> str:
    """
    打码所有可能的密钥。输入任意对象，返回打码后的 str。
    规则：sk-xxx / gsk-xxx 开头 20+字 → ***REDACTED***；任何 32+ 字连续字母数字下划线 → 头尾各4中间***
    """
    try:
        if isinstance(obj, (bytes, bytearray)):
            obj = obj.decode('utf-8', errors='replace')
        text = str(obj)
    except Exception:
        text = repr(obj)

    def _sub_long(m):
        s = m.group(0)
        if len(s) <= 8:
            return s
        return s[:4] + '***' + s[-4:]

    text = _KEY_RE.sub('***REDACTED***', text)
    text = _LONG_KEY_RE.sub(_sub_long, text)
    return text
