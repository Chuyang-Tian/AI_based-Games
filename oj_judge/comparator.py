"""
输出比对器 OutputComparator：给定 actual/expected 两段文本，按 compare_mode 判 AC 或 WA。
= 四种比对模式（common.Comparator 接口要求 Step3 可切换）=
  exact    ：严格逐字符完全相等（包括换行、空格、BOM）。最苛刻，一般不用。
  loose    ：默认 OJ 最常见模式——
             normalize 先每行 rstip 去掉行尾空格，再把首尾空行全部 pop；
             剩下的内容比较。解决"用户多打一个换行/每行末尾多空格"不应该 WA 的问题。
  token    ：先 normalize → 再把每行按 whitespace 切成 tokens，行间插入换行符 \n → 按 token 列表逐个比对，
             容忍"空格数 / 缩进不一致"但 token 顺序一致。
  float    ：token 模式的基础上，额外把数值 token 当浮点数比较，abs 差 < float_precision（默认 1e-6）就判等。
             适合数值计算类题目（如 sqrt/矩阵乘法）。
= 设计意图 =
  把比对策略单独抽成类，避免 Judger.judge() 里写一堆 if-else，新增"自定义比对（如特判器）"时只要加个 mode。
"""
import re
from typing import Tuple


class OutputComparator:
    @staticmethod
    def _normalize(text: str) -> str:
        lines = text.split('\n')
        lines = [line.rstrip() for line in lines]
        while lines and lines[-1] == '':
            lines.pop()
        while lines and lines[0] == '':
            lines.pop(0)
        return '\n'.join(lines)

    @staticmethod
    def _normalize_tokens(text: str) -> str:
        text = OutputComparator._normalize(text)
        tokens = []
        for line in text.split('\n'):
            line_tokens = line.split()
            if line_tokens:
                tokens.extend(line_tokens)
            tokens.append('\n')
        if tokens and tokens[-1] == '\n':
            tokens.pop()
        result = []
        for tok in tokens:
            if tok == '\n':
                result.append('\n')
            else:
                result.append(tok)
                result.append(' ')
        if result and result[-1] == ' ':
            result.pop()
        return ''.join(result)

    @staticmethod
    def compare_exact(actual: str, expected: str) -> bool:
        return OutputComparator._normalize(actual) == OutputComparator._normalize(expected)

    @staticmethod
    def compare_tokens(actual: str, expected: str) -> bool:
        return OutputComparator._normalize_tokens(actual) == OutputComparator._normalize_tokens(expected)

    @staticmethod
    def compare_floats(
        actual: str,
        expected: str,
        precision: float = 1e-6
    ) -> bool:
        actual_norm = OutputComparator._normalize(actual)
        expected_norm = OutputComparator._normalize(expected)
        actual_lines = actual_norm.split('\n')
        expected_lines = expected_norm.split('\n')
        if len(actual_lines) != len(expected_lines):
            return False
        for a_line, e_line in zip(actual_lines, expected_lines):
            a_tokens = a_line.split()
            e_tokens = e_line.split()
            if len(a_tokens) != len(e_tokens):
                return False
            for a_tok, e_tok in zip(a_tokens, e_tokens):
                try:
                    a_val = float(a_tok)
                    e_val = float(e_tok)
                    if abs(a_val - e_val) > precision and abs(a_val - e_val) > precision * abs(e_val):
                        return False
                except (ValueError, TypeError):
                    if a_tok != e_tok:
                        return False
        return True

    @staticmethod
    def diff(actual: str, expected: str) -> Tuple[str, str]:
        a_norm = OutputComparator._normalize(actual)
        e_norm = OutputComparator._normalize(expected)
        a_lines = a_norm.split('\n')
        e_lines = e_norm.split('\n')
        max_lines = max(len(a_lines), len(e_lines))
        diff_a = []
        diff_e = []
        for i in range(max_lines):
            a_line = a_lines[i] if i < len(a_lines) else '<missing>'
            e_line = e_lines[i] if i < len(e_lines) else '<missing>'
            mark = ' ' if a_line == e_line else 'X'
            diff_a.append(f'{mark} L{i+1:3d}: {a_line}')
            diff_e.append(f'{mark} L{i+1:3d}: {e_line}')
        return '\n'.join(diff_a), '\n'.join(diff_e)
