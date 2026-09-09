"""
反 AI 作弊审查模块
=================
5 个维度量化评分（0-100），最后加权汇总：
  overall = 0.35*S1 + 0.25*S2 + 0.15*S3 + 0.15*S4 + 0.10*S5
  ≥70 → high 🔴  40~69 → mid 🟡  <40 → low 🟢

本地离线规则（S2/S3/S4/S5 全离线算，不费 token）：
  S2 代码相似度: difflib.SequenceMatcher 同题其他提交取最高
  S3 提交模式:  一次 AC 率、提交间隔是否过短
  S4 性能异常:  runtime/memory 与同题 avg 偏离程度
  S5 元数据:    账号新、频率突变、首次提交难题AC
  S1 AI 生成概率: 本地启发式 + 可选 LLM 打分（没配 key 时只算本地）
"""

import os
import sys
import re
import math
import difflib
import tokenize
import io
from collections import Counter
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


@dataclass
class AntiCheatResult:
    s1_ai_prob: int = 0
    s2_similarity: int = 0
    s3_submit_pattern: int = 0
    s4_perf_anomaly: int = 0
    s5_metadata: int = 0
    overall: int = 0
    level: str = 'low'  # high/mid/low
    details: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> Dict[str, Any]:
        return {
            's1': self.s1_ai_prob,
            's2': self.s2_similarity,
            's3': self.s3_submit_pattern,
            's4': self.s4_perf_anomaly,
            's5': self.s5_metadata,
            'overall': self.overall,
            'level': self.level,
            'details': self.details,
        }


def _clamp(v: float, lo=0, hi=100) -> int:
    return int(max(lo, min(hi, round(v))))


# ------------------------------ S2：代码相似度 ------------------------------

def _normalize_py(src: str) -> str:
    """去掉注释/文档字符串/多余空白/重命名局部变量（标准化指纹）"""
    try:
        result = []
        tokens = list(tokenize.tokenize(io.BytesIO(src.encode('utf-8')).readline))
        skip_until_indent = False
        for tok in tokens:
            ttype, tval = tok.type, tok.string
            if ttype == tokenize.COMMENT:
                continue
            if ttype == tokenize.STRING:
                prev = result[-1] if result else ''
                if prev in ('def', 'class'):
                    continue
                result.append('STR')
                continue
            if ttype in (tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT):
                continue
            if ttype == tokenize.NAME and re.fullmatch(r'[a-z_][a-z0-9_]*', tval) and len(tval) <= 2:
                result.append('VAR')
            else:
                result.append(tval)
        return ' '.join(result)
    except Exception:
        return re.sub(r'\s+', ' ', src).strip()


def score_s2_similarity(source: str, other_sources: List[str]) -> Tuple[int, Dict[str, Any]]:
    """
    source: 本次提交源码
    other_sources: 同题其他提交（不包括本人同一次）
    返回 (score_0_100, {max_sim, top_n_count})
    """
    if not other_sources:
        return 0, {'max_sim': 0.0, 'count': 0}
    norm_cur = _normalize_py(source)
    sims = []
    for other in other_sources:
        try:
            norm_other = _normalize_py(other)
            if not norm_cur or not norm_other:
                sims.append(0.0)
                continue
            ratio = difflib.SequenceMatcher(None, norm_cur, norm_other).ratio()
            sims.append(ratio)
        except Exception:
            sims.append(0.0)
    if not sims:
        return 0, {'max_sim': 0.0, 'count': 0}
    max_sim = max(sims)
    high_count = sum(1 for s in sims if s >= 0.75)
    score = 0.0
    if max_sim >= 0.95:
        score = 100
    elif max_sim >= 0.85:
        score = 80
    elif max_sim >= 0.75:
        score = 60
    elif max_sim >= 0.6:
        score = 35
    else:
        score = max_sim * 40
    if high_count >= 3:
        score = min(100, score + 15)
    return _clamp(score), {'max_sim': round(max_sim, 4), 'high_match_count': high_count, 'count': len(sims)}


# ------------------------------ S3：提交模式 ------------------------------

def score_s3_submit_pattern(
    *,
    one_shot_ac: bool,
    user_recent_submissions: List[Dict[str, Any]],
    submit_intervals_sec: List[float],
) -> Tuple[int, Dict[str, Any]]:
    """
    one_shot_ac: 本次是否首次提交就AC（同题此前无任何WA/CE/RE）
    user_recent_submissions: 该用户最近 10 次 submission（含本次）status 列表
    submit_intervals_sec: 该用户同题提交之间间隔秒数（升序，相邻两次）
    """
    score = 0.0
    details = {}
    statuses = [s.get('status', '') for s in (user_recent_submissions or [])][:10]
    if one_shot_ac:
        score += 50
    if statuses:
        ac_rate = sum(1 for s in statuses if 'AC' in str(s).upper()) / max(1, len(statuses))
        if len(statuses) >= 5 and ac_rate >= 0.95:
            score += 30
        elif len(statuses) >= 3 and ac_rate == 1.0:
            score += 20
    details['recent_ac_rate'] = round(
        sum(1 for s in statuses if 'AC' in str(s).upper()) / max(1, len(statuses)), 3
    )
    details['one_shot_ac'] = bool(one_shot_ac)
    short_intervals = [x for x in submit_intervals_sec if 0 < x < 8]
    if len(short_intervals) >= 2:
        score += 20
        details['short_submit_count'] = len(short_intervals)
    return _clamp(score), details


# ------------------------------ S4：性能异常 ------------------------------

def score_s4_perf_anomaly(
    *,
    runtime_ms: Optional[float],
    memory_mb: Optional[float],
    peers_avg_runtime_ms: Optional[float],
    peers_avg_memory_mb: Optional[float],
) -> Tuple[int, Dict[str, Any]]:
    score = 0.0
    details = {}
    if runtime_ms is not None and peers_avg_runtime_ms and peers_avg_runtime_ms > 0:
        ratio = runtime_ms / peers_avg_runtime_ms
        details['runtime_ratio_vs_peer_avg'] = round(ratio, 3)
        if ratio <= 0.08 and runtime_ms > 0:
            score += 45
        elif ratio <= 0.15:
            score += 25
    if memory_mb is not None and peers_avg_memory_mb and peers_avg_memory_mb > 0:
        ratio = memory_mb / peers_avg_memory_mb
        details['memory_ratio_vs_peer_avg'] = round(ratio, 3)
        if ratio <= 0.15 and memory_mb > 0:
            score += 25
    if runtime_ms is not None and runtime_ms == 0:
        score += 20
    return _clamp(score), details


# ------------------------------ S5：元数据 ------------------------------

def score_s5_metadata(
    *,
    account_age_days: Optional[float],
    recent_submit_spike_ratio: Optional[float],
    first_submit_is_hard_ac: bool,
    ip_changed_country: bool = False,
) -> Tuple[int, Dict[str, Any]]:
    score = 0.0
    details = {}
    if account_age_days is not None and account_age_days < 1:
        score += 35
        details['brand_new_account'] = True
    if recent_submit_spike_ratio is not None and recent_submit_spike_ratio >= 10:
        score += 35
        details['submit_spike_ratio'] = round(recent_submit_spike_ratio, 2)
    if first_submit_is_hard_ac:
        score += 30
        details['first_submit_hard_ac'] = True
    if ip_changed_country:
        score += 25
        details['ip_country_changed'] = True
    return _clamp(score), details


# ------------------------------ S1：AI 生成概率（本地启发式） ------------------------------

PY_STOPWORDS = {
    'def', 'class', 'return', 'if', 'elif', 'else', 'for', 'while', 'in',
    'import', 'from', 'as', 'with', 'try', 'except', 'finally', 'raise',
    'pass', 'break', 'continue', 'and', 'or', 'not', 'is', 'None', 'True',
    'False', 'lambda', 'yield', 'global', 'nonlocal', 'async', 'await',
}


def _shannon_entropy(text: str) -> float:
    if not text:
        return 0.0
    c = Counter(text)
    n = len(text)
    return -sum((v / n) * math.log2(v / n) for v in c.values())


def _comment_and_docstring_rate(src: str) -> float:
    lines = src.splitlines()
    if not lines:
        return 0.0
    comment_lines = 0
    docstring_mode = False
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if docstring_mode:
            comment_lines += 1
            if '"""' in s or "'''" in s:
                docstring_mode = False
            continue
        if s.startswith('#'):
            comment_lines += 1
            continue
        if s.startswith('"""') or s.startswith("'''"):
            comment_lines += 1
            if s.count('"""') < 2 and s.count("'''") < 2:
                docstring_mode = True
    return comment_lines / len(lines)


def _meaningless_var_rate(src: str) -> float:
    try:
        tokens = list(tokenize.tokenize(io.BytesIO(src.encode('utf-8')).readline))
    except Exception:
        return 0.0
    var_names = []
    for t in tokens:
        if t.type == tokenize.NAME and re.fullmatch(r'[a-z_][a-z0-9_]*', t.string):
            if t.string in PY_STOPWORDS:
                continue
            var_names.append(t.string)
    if not var_names:
        return 0.0
    meaningless = {'a', 'b', 'c', 'd', 'e', 'x', 'y', 'z', 'i', 'j', 'k', 'n', 'm',
                   's', 't', 'u', 'v', 'w', 'p', 'q', 'r', 'f', 'g', 'h', 'o', 'l',
                   'num', 'val', 'res', 'tmp', 'temp', 'cur', 'cnt', 'ans', 'arr'}
    return sum(1 for v in var_names if v in meaningless) / len(var_names)


def score_s1_local(source: str) -> Tuple[int, Dict[str, Any]]:
    """
    纯本地启发式 S1 打分（不费 token）
    """
    score = 0.0
    details = {}
    src = source or ''
    c_rate = _comment_and_docstring_rate(src)
    details['comment_rate'] = round(c_rate, 3)
    if c_rate < 0.03:
        score += 30
    elif c_rate < 0.08:
        score += 15
    mv_rate = _meaningless_var_rate(src)
    details['meaningless_var_rate'] = round(mv_rate, 3)
    if mv_rate > 0.65:
        score += 25
    elif mv_rate > 0.45:
        score += 12
    try:
        import_tokens = set()
        for t in tokenize.tokenize(io.BytesIO(src.encode('utf-8')).readline):
            if t.type == tokenize.NAME and t.string == 'import':
                break
        else:
            pass
        imports = re.findall(r'^\s*(?:from\s+([\w\.]+)|import\s+([\w\., ]+))', src, re.MULTILINE)
        std_count = 0
        total = 0
        stdlibs = {'sys', 'os', 're', 'math', 'collections', 'heapq', 'bisect',
                   'itertools', 'functools', 'string', 'random', 'time', 'json',
                   'typing', 'io', 'queue', 'deque', 'defaultdict', 'Counter',
                   'sortedcontainers', 'copy', 'struct', 'hashlib'}
        for f, i in imports:
            parts = [x.strip() for x in (f or i).split(',') if x.strip()]
            for p in parts:
                root = p.split('.')[0].split()[0]
                total += 1
                if root in stdlibs:
                    std_count += 1
        details['import_stdlib_ratio'] = round(std_count / max(1, total), 3) if total else 0.0
        if total >= 3 and std_count == total:
            score += 15
    except Exception:
        pass
    ent = _shannon_entropy(src)
    details['char_entropy'] = round(ent, 3)
    if ent < 3.2 and len(src) > 300:
        score += 15
    elif ent < 3.6 and len(src) > 500:
        score += 8
    lines = [l.strip() for l in src.splitlines() if l.strip()]
    avg_line_len = sum(len(l) for l in lines) / max(1, len(lines))
    details['avg_line_len'] = round(avg_line_len, 1)
    if avg_line_len > 85:
        score += 10
    return _clamp(score), details


# ------------------------------ 总入口 ------------------------------

def evaluate(
    *,
    source: str,
    other_sources: Optional[List[str]] = None,
    one_shot_ac: bool = False,
    user_recent_submissions: Optional[List[Dict[str, Any]]] = None,
    submit_intervals_sec: Optional[List[float]] = None,
    runtime_ms: Optional[float] = None,
    memory_mb: Optional[float] = None,
    peers_avg_runtime_ms: Optional[float] = None,
    peers_avg_memory_mb: Optional[float] = None,
    account_age_days: Optional[float] = None,
    recent_submit_spike_ratio: Optional[float] = None,
    first_submit_is_hard_ac: bool = False,
    s1_ai_score_from_llm: Optional[int] = None,
) -> AntiCheatResult:
    """
    主入口。所有关键字参数可选，没传的维度计 0 分，weight 按实际算到的维度重新归一化。
    """
    other_sources = other_sources or []
    user_recent_submissions = user_recent_submissions or []
    submit_intervals_sec = submit_intervals_sec or []

    s1_local, d1 = score_s1_local(source)
    if s1_ai_score_from_llm is not None:
        s1 = _clamp(0.5 * s1_local + 0.5 * int(s1_ai_score_from_llm))
        d1['llm_score_used'] = int(s1_ai_score_from_llm)
    else:
        s1 = s1_local
        d1['llm_score_used'] = None
    s2, d2 = score_s2_similarity(source, other_sources)
    s3, d3 = score_s3_submit_pattern(
        one_shot_ac=one_shot_ac,
        user_recent_submissions=user_recent_submissions,
        submit_intervals_sec=submit_intervals_sec,
    )
    s4, d4 = score_s4_perf_anomaly(
        runtime_ms=runtime_ms,
        memory_mb=memory_mb,
        peers_avg_runtime_ms=peers_avg_runtime_ms,
        peers_avg_memory_mb=peers_avg_memory_mb,
    )
    s5, d5 = score_s5_metadata(
        account_age_days=account_age_days,
        recent_submit_spike_ratio=recent_submit_spike_ratio,
        first_submit_is_hard_ac=first_submit_is_hard_ac,
    )
    W = {'s1': 0.35, 's2': 0.25, 's3': 0.15, 's4': 0.15, 's5': 0.10}
    used_weights = sum(v for v in W.values())
    overall_raw = (W['s1'] * s1 + W['s2'] * s2 + W['s3'] * s3 + W['s4'] * s4 + W['s5'] * s5) / used_weights
    overall = _clamp(overall_raw)
    if overall >= 70:
        level = 'high'
    elif overall >= 40:
        level = 'mid'
    else:
        level = 'low'
    result = AntiCheatResult(
        s1_ai_prob=s1, s2_similarity=s2, s3_submit_pattern=s3,
        s4_perf_anomaly=s4, s5_metadata=s5, overall=overall, level=level,
    )
    result.details = {
        's1_ai_prob': d1,
        's2_similarity': d2,
        's3_submit_pattern': d3,
        's4_perf_anomaly': d4,
        's5_metadata': d5,
        'weights': W,
    }
    return result


def build_report_html(r: AntiCheatResult, *, submission_id: int, username: str = '',
                      problem_title: str = '') -> str:
    """生成供 admin 审查的 HTML 报告卡片"""
    level_map = {
        'high': ('🔴 高风险', '#374151'),
        'mid': ('🟡 中风险', '#4b5563'),
        'low': ('🟢 低风险', '#6b7280'),
    }
    label, color = level_map.get(r.level, level_map['low'])
    rows = ''
    D = [
        ('S1', 'AI生成概率', r.s1_ai_prob, r.details.get('s1_ai_prob', {})),
        ('S2', '代码重复率', r.s2_similarity, r.details.get('s2_similarity', {})),
        ('S3', '提交模式', r.s3_submit_pattern, r.details.get('s3_submit_pattern', {})),
        ('S4', '性能异常', r.s4_perf_anomaly, r.details.get('s4_perf_anomaly', {})),
        ('S5', '账号元数据', r.s5_metadata, r.details.get('s5_metadata', {})),
    ]
    for tag, name, score, info in D:
        try:
            info_txt = '; '.join(f'{k}={v}' for k, v in info.items()) if isinstance(info, dict) else str(info)
        except Exception:
            info_txt = ''
        if score >= 70:
            bg = '#f5f5f5'
        elif score >= 40:
            bg = '#f8fafc'
        else:
            bg = '#f9fafb'
        rows += f'''
        <tr style="background:{bg};">
          <td style="padding:8px 12px;border:1px solid #d1d5db;"><b>{tag}</b></td>
          <td style="padding:8px 12px;border:1px solid #d1d5db;">{name}</td>
          <td style="padding:8px 12px;border:1px solid #d1d5db;font-weight:700;">{score}</td>
          <td style="padding:8px 12px;border:1px solid #d1d5db;color:#4b5563;font-size:12px;">{info_txt}</td>
        </tr>'''
    html = f'''
    <div style="max-width:820px;font-family:system-ui,'Microsoft YaHei',sans-serif;border:1px solid #d1d5db;border-radius:10px;overflow:hidden;background:#f9fafb;color:#111827;">
      <div style="background:{color};color:#fff;padding:14px 20px;">
        <div style="font-size:18px;font-weight:700;">🤖 AI 作弊风险审查报告 · Submission #{submission_id}</div>
        <div style="opacity:0.92;margin-top:4px;">用户: <b>{username or '-'}</b> &nbsp;|&nbsp; 题目: <b>{problem_title or '-'}</b> &nbsp;|&nbsp; 综合分: <b>{r.overall}</b> → {label}</div>
      </div>
      <div style="padding:14px 20px;background:#f3f4f6;border-bottom:1px solid #d1d5db;font-size:12.5px;color:#4b5563;">
        加权公式: <code>overall = 0.35·S1 + 0.25·S2 + 0.15·S3 + 0.15·S4 + 0.10·S5</code>；
        ≥70 🔴 高风险，40~69 🟡 中风险，<40 🟢 低风险。本审查仅为管理员提供参考，不自动判定为作弊。
      </div>
      <table style="width:100%;border-collapse:collapse;background:#f9fafb;color:#111827;">
        <thead><tr style="background:#e5e7eb;">
          <th style="padding:10px 12px;text-align:left;border:1px solid #d1d5db;width:60px;">维度</th>
          <th style="padding:10px 12px;text-align:left;border:1px solid #d1d5db;width:140px;">名称</th>
          <th style="padding:10px 12px;text-align:left;border:1px solid #d1d5db;width:90px;">得分</th>
          <th style="padding:10px 12px;text-align:left;border:1px solid #d1d5db;">细节（本地规则计算值）</th>
        </tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>'''
    return html
