# -*- coding: utf-8 -*-
"""题目管理/题库浏览页。"""

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
    page_url,
    render_subheader,
    render_topbar,
    require_login_error,
    toast_safe,
)

st.set_page_config(page_title='题目管理 · OJ', page_icon='🗂', layout='wide', initial_sidebar_state='collapsed')

ensure_init()
render_topbar('题目目录页')
render_subheader([('🏠 判题首页', 'home'), ('🗂 题目管理' if is_admin() else '📚 题库浏览', None)], 'problems')

user = current_user()
if not user:
    require_login_error()
    st.stop()

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
    st.subheader('题目目录', divider=False)
    st.caption('这个页面只负责浏览和筛选；查看、编辑、提交都进入独立页面。')
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        for item in filtered:
            with st.container(border=True):
                left, right1, right2 = st.columns([7, 2, 2])
                with left:
                    st.markdown(f"**{item.get('id')} · {item.get('title')}**")
                    st.caption(
                        f"难度: {item.get('difficulty') or '-'}  |  作者: {item.get('author') or '-'}  |  TL: {item.get('time_limit') or '-'} s  |  ML: {item.get('memory_limit') or '-'} MB"
                    )
                with right1:
                    st.link_button('查看题目', page_url('problem_detail', id=item.get('id')), use_container_width=True)
                with right2:
                    st.link_button('进入判题', page_url('judge', id=item.get('id')), type='primary', use_container_width=True)
    else:
        st.info('没有匹配的题目。')

if is_admin():
    with st.container(border=True):
        st.subheader('新增题目', divider=False)
        with st.form('problem_create_form'):
            c1, c2, c3 = st.columns(3)
            with c1:
                problem_id = st.text_input('题目 ID')
            with c2:
                title = st.text_input('标题')
            with c3:
                difficulty_text = st.selectbox('难度', ['简单', '中等', '困难'], index=1)
            description = st.text_area('题目描述', height=140)
            input_description = st.text_area('输入描述', height=100)
            output_description = st.text_area('输出描述', height=100)
            constraints = st.text_area('数据范围', height=80)
            hint = st.text_area('提示', height=80)
            c4, c5, c6 = st.columns(3)
            with c4:
                author = st.text_input('作者', value=user.get('username') or 'admin')
            with c5:
                source = st.text_input('来源')
            with c6:
                tags = st.text_input('标签（逗号分隔）')
            c7, c8 = st.columns(2)
            with c7:
                time_limit = st.number_input('时间限制', min_value=0.1, step=0.1, value=1.0)
            with c8:
                memory_limit = st.number_input('内存限制', min_value=8, step=8, value=128)
            samples_text = st.text_area('样例 JSON', value=json.dumps([{'input': '', 'output': ''}], ensure_ascii=False, indent=2), height=160)
            testcases_text = st.text_area('测试点 JSON', value=json.dumps([{'input': '', 'output': ''}], ensure_ascii=False, indent=2), height=160)
            create_clicked = st.form_submit_button('创建题目', type='primary', use_container_width=True)

        if create_clicked:
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
                save_code, save_data, save_err = api('POST', '/api/problems/', payload)
                if save_code == 200:
                    clear_problem_cache()
                    toast_safe('题目创建成功', 'ok')
                    st.rerun()
                st.error(f'创建失败：{save_data.get("msg") if save_data else save_err}')
