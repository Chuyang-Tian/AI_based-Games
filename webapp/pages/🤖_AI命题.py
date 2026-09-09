# -*- coding: utf-8 -*-
"""AI 智能命题页。"""

import os
import sys
import time

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import (
    api,
    clear_problem_cache,
    current_user,
    ensure_init,
    is_admin,
    render_page_link,
    render_subheader,
    render_topbar,
    require_login_error,
    toast_safe,
)

st.set_page_config(page_title='AI 命题 · OJ', page_icon='🤖', layout='wide', initial_sidebar_state='collapsed')

ensure_init()
render_topbar('AI 智能命题')
render_subheader([('🏠 判题首页', 'home'), ('🤖 AI 命题', None)], 'ai')

user = current_user()
if not user:
    require_login_error()
    st.stop()


def normalize_problem_payload(problem_json):
    difficulty_value = problem_json.get('difficulty', 5)
    if isinstance(difficulty_value, (int, float)):
        if difficulty_value <= 3:
            difficulty_text = '简单'
        elif difficulty_value <= 7:
            difficulty_text = '中等'
        else:
            difficulty_text = '困难'
    else:
        difficulty_text = str(difficulty_value or '中等')
    test_cases = problem_json.get('test_cases') or []
    samples = [
        {'input': item.get('input', ''), 'output': item.get('output', '')}
        for item in test_cases if item.get('visibility') == 'public'
    ]
    if not samples and test_cases:
        samples = [{'input': test_cases[0].get('input', ''), 'output': test_cases[0].get('output', '')}]
    payload = {
        'id': problem_json.get('problem_id_hint') or f"ai_{int(time.time())}",
        'title': problem_json.get('title') or 'AI 生成题目',
        'description': problem_json.get('description') or '',
        'input_description': '详见题面中的输入格式部分。',
        'output_description': '详见题面中的输出格式部分。',
        'constraints': '详见题面中的数据范围部分。',
        'samples': samples,
        'testcases': [{'input': item.get('input', ''), 'output': item.get('output', '')} for item in test_cases],
        'hint': '',
        'source': 'AI 智能命题',
        'tags': problem_json.get('tags') or [],
        'time_limit': float(problem_json.get('time_limit') or 1.0),
        'memory_limit': int(problem_json.get('memory_limit') or 128),
        'author': user.get('username') or 'AI',
        'difficulty': difficulty_text,
    }
    return payload


config_code, config_data, _ = api('GET', '/api/ai/config')
config = config_data.get('data') if isinstance(config_data, dict) else {}
if not config.get('configured') and not config.get('mock_mode'):
    st.warning('当前尚未配置 AI 密钥。请先到“AI 配置”页面保存模型参数，或者启用 Mock 模式。')

with st.container(border=True):
    st.subheader('创建命题任务', divider=False)
    with st.form('ai_task_form'):
        c1, c2 = st.columns(2)
        with c1:
            topic = st.text_input('主题 / 知识点', placeholder='例如：二分答案、最短路、动态规划')
            difficulty = st.slider('难度（1-10）', min_value=1, max_value=10, value=5)
            sample_count = st.number_input('样例数量', min_value=1, max_value=8, value=4)
        with c2:
            style = st.selectbox('题面风格', ['plain', 'story', 'contest'], index=0)
            complexity_target = st.text_input('期望复杂度', value='O(n log n)')
            extra_tags = st.text_input('附加标签', placeholder='数组, 排序, 贪心')
        requirement = st.text_area('补充要求', height=120, placeholder='描述边界样例、输入规模、是否要有故事背景等')
        submit = st.form_submit_button('发起 AI 命题任务', type='primary', use_container_width=True)
    if submit:
        payload = {
            'topic': topic.strip() or requirement.strip() or '基础算法',
            'difficulty': int(difficulty),
            'style': style,
            'sample_count': int(sample_count),
            'complexity_target': complexity_target.strip() or 'O(n log n)',
            'extra_tags': [item.strip() for item in extra_tags.split(',') if item.strip()],
            'source': 'AI 智能命题',
            'style_custom': requirement.strip(),
        }
        task_code, task_data, task_err = api('POST', '/api/ai/problem-tasks/', payload, timeout=120)
        if task_code == 200 and isinstance(task_data, dict) and task_data.get('data'):
            st.session_state['ai_active_task_id'] = task_data['data'].get('task_id')
            st.session_state.pop('ai_latest_result', None)
            toast_safe('AI 任务已创建', 'ok')
            st.rerun()
        st.error(f'任务创建失败：{task_data.get("msg") if task_data else task_err}')


def render_task_status():
    task_id = st.session_state.get('ai_active_task_id')
    if not task_id:
        st.info('当前没有进行中的 AI 任务。')
        return
    status_code, status_data, status_err = api('GET', f'/api/ai/problem-tasks/{task_id}')
    if status_code != 200 or not isinstance(status_data, dict) or not status_data.get('data'):
        st.error(f'读取任务状态失败：{status_data.get("msg") if status_data else status_err}')
        return
    task = status_data['data']
    last_payload = task.get('last_payload') or {}
    status = task.get('status') or 'running'
    cols = st.columns(4)
    cols[0].metric('任务 ID', task_id[:8])
    cols[1].metric('当前状态', status)
    cols[2].metric('最后事件', task.get('last_event') or '-')
    cols[3].metric('完成时间', task.get('finished_at') or '-')
    if task.get('last_event') == 'step':
        step_index = int(last_payload.get('index', 0) or 0)
        step_total = int(last_payload.get('total', 5) or 5)
        st.progress(min(step_index / max(step_total, 1), 1.0))
        st.caption(f"{last_payload.get('title', '')}：{last_payload.get('text', '')}")
    elif task.get('last_event') == 'token':
        st.caption(f"已消耗输入 {last_payload.get('input_tokens', 0)} tokens，输出 {last_payload.get('output_tokens', 0)} tokens。")
    elif task.get('last_event') == 'retried':
        st.warning(f"自动重试中：{last_payload.get('reason', '')}")
    elif task.get('last_event') == 'error':
        st.error(task.get('error_message') or last_payload.get('message') or '任务失败')
    if task.get('html_preview'):
        st.markdown(task.get('html_preview'), unsafe_allow_html=True)
    if task.get('result'):
        st.session_state['ai_latest_result'] = task.get('result')
        st.session_state.pop('ai_active_task_id', None)
    elif status in ('error', 'cancelled'):
        st.session_state.pop('ai_active_task_id', None)


with st.container(border=True):
    st.subheader('任务进度', divider=False)
    if hasattr(st, 'fragment'):
        @st.fragment(run_every='2s')
        def task_fragment():
            render_task_status()
        task_fragment()
    else:
        render_task_status()
        if st.button('刷新任务状态', use_container_width=True):
            st.rerun()
    active_task_id = st.session_state.get('ai_active_task_id')
    if active_task_id:
        if st.button('取消当前任务', use_container_width=True):
            cancel_code, cancel_data, cancel_err = api('POST', f'/api/ai/problem-tasks/{active_task_id}/cancel', {})
            if cancel_code == 200:
                toast_safe('任务已取消', 'warn')
                st.session_state.pop('ai_active_task_id', None)
                st.rerun()
            st.error(f'取消失败：{cancel_data.get("msg") if cancel_data else cancel_err}')

result = st.session_state.get('ai_latest_result')
with st.container(border=True):
    st.subheader('生成结果', divider=False)
    if not result:
        st.info('任务完成后会在这里展示题目 JSON，并可一键写入题库。')
    else:
        st.json(result, expanded=False)
        save_payload = normalize_problem_payload(result)
        save_col, judge_col = st.columns(2)
        with save_col:
            if st.button('保存到题库', type='primary', use_container_width=True):
                save_code, save_data, save_err = api('POST', '/api/problems/', save_payload)
                if save_code == 200:
                    clear_problem_cache()
                    st.session_state['ai_saved_problem_id'] = save_payload['id']
                    toast_safe('题目已写入题库', 'ok')
                    st.rerun()
                st.error(f'保存失败：{save_data.get("msg") if save_data else save_err}')
        with judge_col:
            saved_problem_id = st.session_state.get('ai_saved_problem_id') or save_payload['id']
            render_page_link('打开题目管理页', '/%E9%A2%98%E7%9B%AE%E7%AE%A1%E7%90%86')
            st.caption(f'目标题目 ID：`{saved_problem_id}`')
