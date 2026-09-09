# -*- coding: utf-8 -*-
"""
判题器（纵向 OJ 布局版）
"""
import json
import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(page_title='判题器 · OJ', page_icon='⚖️', layout='wide', initial_sidebar_state='collapsed')

from common import (  # noqa: E402
    api,
    current_user,
    ensure_init,
    get_locale,
    goto,
    is_admin,
    load_all_problems,
    load_languages,
    page_url,
    render_home_button,
    render_page_link,
    render_rich_text,
    render_sample_cases,
    render_subheader,
    render_topbar,
    require_login_error,
    toast_safe,
    tr,
)


def t(zh: str, en: str) -> str:
    return en if get_locale() == 'en-US' else zh


ensure_init()
user = current_user()
render_topbar(tr('page_judge', '独立判题页'))

raw_pid = st.query_params.get('id') or ''
pid = str(raw_pid[0]) if isinstance(raw_pid, (list, tuple)) and raw_pid else str(raw_pid or '')
raw_assignment_id = st.query_params.get('assignment_id') or ''
assignment_id = str(raw_assignment_id[0]) if isinstance(raw_assignment_id, (list, tuple)) and raw_assignment_id else str(raw_assignment_id or '')
raw_exam_id = st.query_params.get('exam_id') or ''
exam_id = str(raw_exam_id[0]) if isinstance(raw_exam_id, (list, tuple)) and raw_exam_id else str(raw_exam_id or '')

if not pid:
    st.info(t('⚠️ 没有指定题目 ID（URL 需包含 ?id=xxx）。', '⚠️ Missing problem ID (`?id=xxx` is required in URL).'))
    render_home_button(t('← 返回首页', '← Back Home'))
    st.stop()

problems = load_all_problems()
problem = next((p for p in problems if str(p.get('id', '')) == pid), None)
if not problem:
    c, d, _ = api('GET', f'/api/problems/{pid}')
    if c == 200 and d and d.get('data'):
        problem = d['data']

breadcrumbs = [(t('🏠 判题首页', '🏠 Home'), 'home')]
if assignment_id:
    breadcrumbs.append((t('📝 作业', '📝 Assignment'), 'assignments'))
if exam_id:
    breadcrumbs.append((t('📝 考试', '📝 Exam'), 'exams'))
breadcrumbs.append((t('🗂 题目管理', '🗂 Problem Admin') if is_admin() else t('📚 题库', '📚 Problemset'), 'problems'))
if problem:
    breadcrumbs.append((f'📝 {problem.get("id")} · {problem.get("title")}', None))
else:
    breadcrumbs.append((t('题目不存在', 'Problem Not Found'), None))
render_subheader(breadcrumbs, 'judge')

if not user:
    require_login_error()
    st.stop()

if not problem:
    st.error(t(f'❌ 题目 `{pid}` 不存在。', f'❌ Problem `{pid}` does not exist.'))
    render_home_button(t('← 返回首页', '← Back Home'))
    st.stop()


@st.cache_data(show_spinner=False, ttl=300)
def get_langs():
    return [{'name': name} for name in load_languages()]


langs = get_langs()
lang_names = [l['name'] for l in langs]
if 'python' not in lang_names:
    lang_names = ['python'] + lang_names

ss = st.session_state
pk = f'judge_{pid}_'


def gs(key, default=None):
    return ss.get(pk + key, default)


def ss_set(key, value):
    ss[pk + key] = value


def is_legacy_starter(code_text: str) -> bool:
    text = str(code_text or '').strip()
    legacy_prefixes = [
        '# 在这里写 Python 3 代码',
        '// C++17',
        'import java.util.*;',
        '// Node.js 20',
    ]
    return any(text.startswith(prefix) for prefix in legacy_prefixes)


if not gs('inited'):
    default_lang = str(problem.get('language') or 'python').strip().lower()
    if default_lang not in lang_names and lang_names:
        default_lang = lang_names[0]
    ss_set('inited', True)
    ss_set('lang', default_lang)
    ss_set('code', '')
    ss_set('tl', float(problem.get('time_limit') or 1.0))
    ss_set('ml', int(problem.get('memory_limit') or 128))
    ss_set('cm', problem.get('compare_mode') or 'exact')
    ss_set('samples', True)
    ss_set('custom', False)
    ss_set('custom_list', [])
elif is_legacy_starter(gs('code', '')):
    ss_set('code', '')

p_title = problem.get('title') or ''
p_id = problem.get('id') or ''
p_diff = problem.get('difficulty') or ''
p_tags = problem.get('tags') or []
p_author = problem.get('author') or 'system'
p_source = problem.get('source') or 'N/A'
p_tl = problem.get('time_limit') or '?'
p_ml = problem.get('memory_limit') or '?'
samples = problem.get('samples') or []

with st.container(border=True):
    left, right = st.columns([8, 2])
    with left:
        st.subheader(f'📖 {p_id} · {p_title}', divider=False)
        meta = (
            t('难度', 'Difficulty') + f': {p_diff or "-"}  |  ' +
            t('作者', 'Author') + f': {p_author}  |  ' +
            t('来源', 'Source') + f': {p_source}'
        )
        if p_tags:
            meta += f'  |  {t("标签", "Tags")}: {", ".join(p_tags)}'
        st.caption(meta)
    with right:
        render_home_button(t('← 返回首页', '← Back Home'))

    m1, m2, m3 = st.columns(3)
    m1.metric(t('⏱ 时间限制', '⏱ Time Limit'), f'{p_tl} s')
    m2.metric(t('💾 内存限制', '💾 Memory Limit'), f'{p_ml} MB')
    m3.metric(t('🧑‍🏫 出题 / 来源', '🧑‍🏫 Author / Source'), f'{p_author} / {p_source}')

    if problem.get('description'):
        st.markdown(f'#### {t("📝 题目描述", "📝 Description")}')
        render_rich_text(problem.get('description'))
    if problem.get('input_description'):
        st.markdown(f'#### {t("📥 输入描述", "📥 Input")}')
        render_rich_text(problem.get('input_description'))
    if problem.get('output_description'):
        st.markdown(f'#### {t("🎯 输出描述", "🎯 Output")}')
        render_rich_text(problem.get('output_description'))
    if problem.get('constraints') or problem.get('hint'):
        extra = str(problem.get('constraints') or '')
        if problem.get('hint'):
            extra += ('\n\n💡 ' + str(problem.get('hint')))
        st.markdown(f'#### {t("⚙️ 数据范围与提示", "⚙️ Constraints & Notes")}')
        render_rich_text(extra)

with st.container(border=True):
    st.subheader(t('📋 公开样例', '📋 Public Samples'), divider=False)
    render_sample_cases(samples, t('公开样例', 'Public Samples'))

with st.container(border=True):
    st.subheader(t('💻 判题工作区', '💻 Judge Workspace'), divider=False)
    st.caption(t(
        '这里不再自动注入任何模板代码。Python 可以直接使用 `input()`，C++ 可以直接使用 `cin`，Java 可以直接使用 `Scanner`。',
        'No starter template is injected here. Python can use `input()`, C++ can use `cin`, and Java can use `Scanner` directly.'
    ))

    row1, row2, row3, row4 = st.columns([2.5, 2.5, 2, 2])
    cur_lang = gs('lang')
    if cur_lang not in lang_names and lang_names:
        cur_lang = lang_names[0]
    with row1:
        new_lang = st.selectbox(
            t('语言', 'Language'),
            lang_names,
            index=lang_names.index(cur_lang),
            key=pk + 'lang',
        )
        if new_lang != cur_lang:
            ss_set('lang', new_lang)
            st.rerun()
    with row2:
        compare_modes = ['exact', 'trim', 'numeric']
        compare_labels = {
            'exact': t('精确(行对比)', 'Exact'),
            'trim': t('Trim 去首尾空格', 'Trim'),
            'numeric': t('数值容差', 'Numeric'),
        }
        cur_cm = gs('cm') or 'exact'
        new_cm_label = st.selectbox(
            t('对比方式', 'Compare Mode'),
            [compare_labels[item] for item in compare_modes],
            index=compare_modes.index(cur_cm if cur_cm in compare_modes else 'exact'),
            key=pk + 'cm',
        )
        ss_set('cm', compare_modes[[compare_labels[item] for item in compare_modes].index(new_cm_label)])
    with row3:
        tl_val = st.number_input(
            t('时间限制 (s)', 'Time Limit (s)'),
            min_value=0.1,
            max_value=60.0,
            step=0.1,
            value=float(gs('tl') or 1.0),
            key=pk + 'tl',
        )
    with row4:
        ml_val = st.number_input(
            t('内存限制 (MB)', 'Memory Limit (MB)'),
            min_value=8,
            max_value=2048,
            step=8,
            value=int(gs('ml') or 128),
            key=pk + 'ml',
        )

    cur_code = st.text_area(
        t('代码编辑器', 'Code Editor'),
        value=gs('code') or '',
        height=420,
        key=pk + 'code',
        help=t(
            '按一般 OJ 习惯直接写代码即可，不需要任何系统模板。',
            'Write code directly like a typical OJ. No system starter template is required.'
        ),
    )

    st.markdown(f'#### {t("🧪 运行设置", "🧪 Run Setup")}')
    judge_mode_label = t('评测', 'Judge')
    custom_mode_label = t('自定义调试', 'Custom Debug')
    default_modes = []
    if gs('samples', True):
        default_modes.append(judge_mode_label)
    if gs('custom', False):
        default_modes.append(custom_mode_label)
    selected_modes = st.multiselect(
        t('本次运行方式', 'Run Mode'),
        [judge_mode_label, custom_mode_label],
        default=default_modes or [judge_mode_label],
        key=pk + 'run_modes',
        help=t(
            '评测：运行题目公开样例。自定义调试：运行你手动填写的样例。',
            'Judge: run official public samples. Custom Debug: run your own cases.'
        ),
    )
    use_samples = judge_mode_label in selected_modes
    use_custom = custom_mode_label in selected_modes
    ss_set('samples', use_samples)
    ss_set('custom', use_custom)

    st.caption(t(
        f'本次将运行 {len(samples) if use_samples else 0} 个公开样例 + {len(gs("custom_list") or []) if use_custom else 0} 个自定义样例。',
        f'This run will use {len(samples) if use_samples else 0} public cases + {len(gs("custom_list") or []) if use_custom else 0} custom cases.'
    ))

    st.markdown(f'#### {t("🔥 自定义调试样例", "🔥 Custom Debug Cases")}')
    add_left, add_right = st.columns([7, 2])
    with add_left:
        st.caption(t(
            '下面是你自己的测试输入和期望输出，只用于本次调试，不会写回题库。',
            'These are your own input/output cases for this debug run only and will not be saved into the problem.'
        ))
    with add_right:
        if st.button(t('＋ 新增一组', '＋ Add Case'), key=pk + 'add_case', use_container_width=True):
            custom_list = list(gs('custom_list') or [])
            custom_list.append({'input': '', 'output': ''})
            ss_set('custom_list', custom_list)
            st.rerun()

    custom_list = list(gs('custom_list') or [])
    if not custom_list:
        st.caption(t('（暂无自定义样例）', '(No custom cases yet)'))
    else:
        next_cases = []
        removed = False
        for idx, case in enumerate(custom_list):
            with st.expander(t(f'样例 #{idx + 1}', f'Case #{idx + 1}'), expanded=True):
                ci, co, cd = st.columns([6, 6, 1])
                with ci:
                    case_input = st.text_area(
                        t('输入', 'Input'),
                        value=case.get('input', ''),
                        height=100,
                        key=f'{pk}custom_in_{idx}',
                    )
                with co:
                    case_output = st.text_area(
                        t('期望输出', 'Expected Output'),
                        value=case.get('output', ''),
                        height=100,
                        key=f'{pk}custom_out_{idx}',
                    )
                with cd:
                    st.caption('')
                    if st.button(t('删除', 'Delete'), key=f'{pk}remove_{idx}', use_container_width=True):
                        removed = True
                        continue
                next_cases.append({'input': case_input, 'output': case_output})
        ss_set('custom_list', next_cases)
        if removed:
            st.rerun()

    submit_col1, submit_col2 = st.columns([7, 3])
    with submit_col2:
        submit = st.button(t('▶ 提交判题', '▶ Submit'), type='primary', use_container_width=True, key=pk + 'submit')

    if submit:
        if not use_samples and not use_custom:
            st.warning(t('请至少选择一种运行方式。', 'Please choose at least one run mode.'))
            st.stop()

        custom_payload_cases = [
            {'input': item.get('input', ''), 'expected': item.get('output', '')}
            for item in (gs('custom_list') or [])
            if (item.get('input') or item.get('output'))
        ]
        if use_custom and not custom_payload_cases:
            st.warning(t('你选择了自定义调试，但还没有填写样例。', 'Custom Debug is selected, but no case has been filled in yet.'))
            st.stop()

        payload = {
            'problem_id': p_id,
            'language': gs('lang'),
            'code': cur_code or '',
            'time_limit': float(tl_val),
            'memory_limit': int(ml_val),
            'compare_mode': gs('cm') or 'exact',
        }
        if assignment_id:
            payload['assignment_id'] = int(assignment_id)
        if exam_id:
            payload['exam_id'] = int(exam_id)
        if use_samples and samples:
            payload['samples_override'] = [
                {'input': item.get('input', ''), 'expected': item.get('output', '')}
                for item in samples
            ]
        if use_custom and custom_payload_cases:
            payload['custom_cases'] = custom_payload_cases
        if use_custom and not use_samples:
            payload['only_custom_cases'] = True

        with st.spinner(t('正在提交判题…', 'Submitting...')):
            c, d, err = api('POST', '/api/submissions/', payload)
        if c == 200 and d and d.get('data'):
            sub = d['data']
            if sub.get('language_corrected_from'):
                toast_safe(
                    t(
                        f'已自动将语言从 {sub.get("language_corrected_from")} 调整为 {sub.get("language")} 。',
                        f'Language auto-corrected from {sub.get("language_corrected_from")} to {sub.get("language")}.'
                    ),
                    'warn',
                )
            sid = sub.get('submission_id') or sub.get('id')
            if not sid:
                st.error(t('后端未返回 submission_id。', 'Backend did not return submission_id.'))
            else:
                goto('submission_detail', id=sid)
        else:
            st.error(t(
                f'提交失败：{d.get("msg") if d else err} (HTTP {c})',
                f'Submit failed: {d.get("msg") if d else err} (HTTP {c})'
            ))

    st.caption(t(
        '提交后会直接跳转到独立评测详情页，方便第一时间查看成绩和各测试点情况。',
        'After submission, the page jumps directly to the dedicated result page so you can immediately inspect the score and testcase details.'
    ))

st.caption(t('© OJ 在线判题平台 · Streamlit 前端 + FastAPI 后端（Python 双栈架构）', '© OJ Platform · Streamlit frontend + FastAPI backend'))
