# -*- coding: utf-8 -*-
"""题目管理页。"""

import json
import os
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import (
    api,
    clear_problem_cache,
    current_user,
    ensure_init,
    get_filtered_problems,
    is_admin,
    load_all_problems,
    render_subheader,
    render_topbar,
    require_login_error,
    toast_safe,
)

st.set_page_config(page_title='题目管理 · OJ', page_icon='🗂', layout='wide', initial_sidebar_state='collapsed')

ensure_init()
render_topbar('题目管理')
render_subheader([('🏠 判题首页', 'home'), ('🗂 题目管理', None)], 'problems')

user = current_user()
if not user:
    require_login_error()
    st.stop()

is_adm = is_admin()
problems = load_all_problems(force=st.session_state.pop('problems_force_refresh', False))

with st.container(border=True):
    st.subheader('题库筛选', divider=False)
    c1, c2, c3 = st.columns([4, 2, 2])
    with c1:
        keyword = st.text_input('搜索题目', value=st.session_state.get('problem_keyword', ''), placeholder='输入题号或标题')
    with c2:
        difficulty = st.selectbox('难度', ['', '简单', '中等', '困难'])
    with c3:
        if st.button('刷新题库', use_container_width=True):
            st.session_state['problems_force_refresh'] = True
            clear_problem_cache()
            st.rerun()
    st.session_state['problem_keyword'] = keyword

filtered = get_filtered_problems(problems, st.session_state.get('problem_keyword', ''), difficulty, [])

rows = []
for item in filtered:
    rows.append({
        '题目 ID': item.get('id'),
        '标题': item.get('title'),
        '难度': item.get('difficulty'),
        '作者': item.get('author'),
        '时间限制': item.get('time_limit'),
        '内存限制': item.get('memory_limit'),
    })

with st.container(border=True):
    st.subheader('题目列表', divider=False)
    st.caption(f'当前共有 {len(filtered)} 道题目。')
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info('没有匹配的题目。')

selected_problem = None
if filtered:
    selected_id = st.selectbox('选择题目查看/编辑', [item.get('id') for item in filtered])
    selected_problem = next((item for item in filtered if item.get('id') == selected_id), None)

if selected_problem:
    with st.container(border=True):
        st.subheader(f"题目详情：{selected_problem.get('id')}", divider=False)
        st.write(selected_problem.get('description', ''))
        st.caption(f"标签：{', '.join(selected_problem.get('tags') or []) or '-'}")
        st.code(json.dumps(selected_problem.get('samples') or [], ensure_ascii=False, indent=2), language='json')
        st.code(json.dumps(selected_problem.get('testcases') or [], ensure_ascii=False, indent=2), language='json')

if is_adm:
    default_problem = selected_problem or {
        'id': '',
        'title': '',
        'description': '',
        'input_description': '',
        'output_description': '',
        'constraints': '',
        'samples': [{'input': '', 'output': ''}],
        'testcases': [{'input': '', 'output': ''}],
        'hint': '',
        'source': '',
        'tags': [],
        'time_limit': 1.0,
        'memory_limit': 128,
        'author': user.get('username') or 'admin',
        'difficulty': '中等',
    }
    with st.container(border=True):
        st.subheader('新增 / 编辑题目', divider=False)
        with st.form('problem_edit_form'):
            c1, c2, c3 = st.columns(3)
            with c1:
                problem_id = st.text_input('题目 ID', value=default_problem.get('id', ''))
            with c2:
                title = st.text_input('标题', value=default_problem.get('title', ''))
            with c3:
                difficulty_text = st.selectbox('难度', ['简单', '中等', '困难'], index=['简单', '中等', '困难'].index(default_problem.get('difficulty', '中等')))
            description = st.text_area('题目描述', value=default_problem.get('description', ''), height=140)
            input_description = st.text_area('输入描述', value=default_problem.get('input_description', ''), height=100)
            output_description = st.text_area('输出描述', value=default_problem.get('output_description', ''), height=100)
            constraints = st.text_area('数据范围', value=default_problem.get('constraints', ''), height=80)
            c4, c5, c6 = st.columns(3)
            with c4:
                author = st.text_input('作者', value=default_problem.get('author', ''))
            with c5:
                source = st.text_input('来源', value=default_problem.get('source', ''))
            with c6:
                tags = st.text_input('标签（逗号分隔）', value=', '.join(default_problem.get('tags') or []))
            hint = st.text_area('提示', value=default_problem.get('hint', ''), height=80)
            c7, c8 = st.columns(2)
            with c7:
                time_limit = st.number_input('时间限制', min_value=0.1, step=0.1, value=float(default_problem.get('time_limit') or 1.0))
            with c8:
                memory_limit = st.number_input('内存限制', min_value=8, step=8, value=int(default_problem.get('memory_limit') or 128))
            samples_text = st.text_area(
                '样例 JSON',
                value=json.dumps(default_problem.get('samples') or [], ensure_ascii=False, indent=2),
                height=160,
            )
            testcases_text = st.text_area(
                '测试点 JSON',
                value=json.dumps(default_problem.get('testcases') or [], ensure_ascii=False, indent=2),
                height=160,
            )
            save_col, delete_col = st.columns(2)
            save_clicked = save_col.form_submit_button('保存题目', type='primary', use_container_width=True)
            delete_clicked = delete_col.form_submit_button('删除当前题目', use_container_width=True, disabled=not selected_problem)

        if save_clicked:
            try:
                samples = json.loads(samples_text)
                testcases = json.loads(testcases_text)
            except Exception as exc:
                st.error(f'JSON 解析失败：{exc}')
            else:
                payload = {
                    'id': problem_id.strip(),
                    'title': title.strip(),
                    'description': description,
                    'input_description': input_description,
                    'output_description': output_description,
                    'constraints': constraints,
                    'samples': samples,
                    'testcases': testcases,
                    'hint': hint,
                    'source': source.strip(),
                    'tags': [item.strip() for item in tags.split(',') if item.strip()],
                    'time_limit': float(time_limit),
                    'memory_limit': int(memory_limit),
                    'author': author.strip(),
                    'difficulty': difficulty_text,
                }
                if selected_problem and selected_problem.get('id') == payload['id']:
                    save_code, save_data, save_err = api('PUT', f"/api/problems/{payload['id']}", payload)
                else:
                    save_code, save_data, save_err = api('POST', '/api/problems/', payload)
                if save_code == 200:
                    clear_problem_cache()
                    toast_safe('题目保存成功', 'ok')
                    st.session_state['problems_force_refresh'] = True
                    st.rerun()
                st.error(f'保存失败：{save_data.get("msg") if save_data else save_err}')

        if delete_clicked and selected_problem:
            delete_code, delete_data, delete_err = api('DELETE', f"/api/problems/{selected_problem['id']}")
            if delete_code == 200:
                clear_problem_cache()
                toast_safe('题目删除成功', 'ok')
                st.session_state['problems_force_refresh'] = True
                st.rerun()
            st.error(f'删除失败：{delete_data.get("msg") if delete_data else delete_err}')

    if selected_problem:
        with st.container(border=True):
            st.subheader('评测日志可见性', divider=False)
            public_cases = st.checkbox('公开测试点明细', value=bool(selected_problem.get('public_cases', False)))
            if st.button('保存日志可见性', use_container_width=True):
                visibility_code, visibility_data, visibility_err = api(
                    'PUT',
                    f"/api/problems/{selected_problem['id']}/log_visibility",
                    {'public_cases': public_cases},
                )
                if visibility_code == 200:
                    toast_safe('日志可见性已更新', 'ok')
                    clear_problem_cache()
                    st.session_state['problems_force_refresh'] = True
                    st.rerun()
                st.error(f'更新失败：{visibility_data.get("msg") if visibility_data else visibility_err}')
