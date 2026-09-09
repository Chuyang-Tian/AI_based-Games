# -*- coding: utf-8 -*-
"""题目详情页。"""

import json
import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import (
    api,
    clear_problem_cache,
    current_user,
    ensure_init,
    is_admin,
    page_url,
    render_page_link,
    render_home_button,
    render_sample_cases,
    render_rich_text,
    render_subheader,
    render_topbar,
    require_login_error,
    toast_safe,
)

st.set_page_config(page_title='题目详情 · OJ', page_icon='📄', layout='wide', initial_sidebar_state='collapsed')

ensure_init()
render_topbar('独立题目页')

user = current_user()
if not user:
    require_login_error()
    st.stop()

raw_pid = st.query_params.get('id') or ''
pid = str(raw_pid[0] if isinstance(raw_pid, list) else raw_pid)

if not pid:
    render_subheader([('🏠 判题首页', 'home'), ('📄 题目详情', None)], 'problems')
    st.warning('缺少题目 ID。')
    render_home_button()
    st.stop()

code, data, err = api('GET', f'/api/problems/{pid}')
problem = data.get('data') if code == 200 and isinstance(data, dict) else None

crumbs = [('🏠 判题首页', 'home'), ('🗂 题目管理' if is_admin() else '📚 题库浏览', 'problems')]
crumbs.append((f'📄 {pid}', None))
render_subheader(crumbs, 'problems')

if not problem:
    st.error(f'题目加载失败：{data.get("msg") if isinstance(data, dict) else err}')
    render_home_button()
else:
    with st.container(border=True):
        top_left, top_mid, top_right = st.columns([6, 2, 2])
        with top_left:
            st.subheader(f"{problem.get('id')} · {problem.get('title')}", divider=False)
            st.caption(
                f"难度: {problem.get('difficulty') or '-'}  |  作者: {problem.get('author') or '-'}  |  来源: {problem.get('source') or '-'}"
            )
        with top_mid:
            render_home_button()
        with top_right:
            render_page_link('进入判题页', page_url('judge', id=problem.get('id')), primary=True)

        m1, m2, m3 = st.columns(3)
        m1.metric('时间限制', f"{problem.get('time_limit') or '-'} s")
        m2.metric('内存限制', f"{problem.get('memory_limit') or '-'} MB")
        m3.metric('公开测试点', '开启' if problem.get('public_cases') else '关闭')

    tabs = st.tabs(['题面详情', '样例与测试点'] + (['管理配置'] if is_admin() else []))

    with tabs[0]:
        st.markdown('#### 题目描述')
        render_rich_text(problem.get('description'), '暂无描述')
        st.markdown('#### 输入描述')
        render_rich_text(problem.get('input_description'), '暂无输入描述')
        st.markdown('#### 输出描述')
        render_rich_text(problem.get('output_description'), '暂无输出描述')
        st.markdown('#### 数据范围与提示')
        render_rich_text((problem.get('constraints') or '') + ('\n\n' + problem.get('hint') if problem.get('hint') else ''), '暂无数据范围与提示')
        if problem.get('tags'):
            st.caption('标签：' + ', '.join(problem.get('tags') or []))

    with tabs[1]:
        render_sample_cases(problem.get('samples') or [], '公开样例')
        if is_admin():
            st.markdown('#### 测试点数据')
            st.code(json.dumps(problem.get('testcases') or [], ensure_ascii=False, indent=2), language='json')

if is_admin() and problem:
    with tabs[2]:
        with st.form('problem_detail_edit_form'):
            c1, c2, c3 = st.columns(3)
            with c1:
                title = st.text_input('标题', value=problem.get('title', ''))
            with c2:
                difficulty = st.selectbox('难度', ['简单', '中等', '困难'], index=['简单', '中等', '困难'].index(problem.get('difficulty', '中等')))
            with c3:
                author = st.text_input('作者', value=problem.get('author', ''))
            description = st.text_area('题目描述', value=problem.get('description', ''), height=140)
            input_description = st.text_area('输入描述', value=problem.get('input_description', ''), height=100)
            output_description = st.text_area('输出描述', value=problem.get('output_description', ''), height=100)
            constraints = st.text_area('数据范围', value=problem.get('constraints', ''), height=100)
            hint = st.text_area('提示', value=problem.get('hint', ''), height=80)
            c4, c5, c6 = st.columns(3)
            with c4:
                source = st.text_input('来源', value=problem.get('source', ''))
            with c5:
                time_limit = st.number_input('时间限制', min_value=0.1, step=0.1, value=float(problem.get('time_limit') or 1.0))
            with c6:
                memory_limit = st.number_input('内存限制', min_value=8, step=8, value=int(problem.get('memory_limit') or 128))
            tags = st.text_input('标签（逗号分隔）', value=', '.join(problem.get('tags') or []))
            samples_text = st.text_area('样例 JSON', value=json.dumps(problem.get('samples') or [], ensure_ascii=False, indent=2), height=160)
            testcases_text = st.text_area('测试点 JSON', value=json.dumps(problem.get('testcases') or [], ensure_ascii=False, indent=2), height=160)
            public_cases = st.checkbox('公开测试点明细', value=bool(problem.get('public_cases', False)))
            save_col, delete_col = st.columns(2)
            save_clicked = save_col.form_submit_button('保存题目', type='primary', use_container_width=True)
            delete_clicked = delete_col.form_submit_button('删除题目', use_container_width=True)

        if save_clicked:
            try:
                samples = json.loads(samples_text)
                testcases = json.loads(testcases_text)
            except Exception as exc:
                st.error(f'JSON 解析失败：{exc}')
            else:
                payload = {
                    'id': problem.get('id'),
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
                    'difficulty': difficulty,
                }
                save_code, save_data, save_err = api('PUT', f"/api/problems/{problem['id']}", payload)
                if save_code == 200:
                    visibility_code, visibility_data, visibility_err = api(
                        'PUT',
                        f"/api/problems/{problem['id']}/log_visibility",
                        {'public_cases': public_cases},
                    )
                    if visibility_code != 200:
                        st.error(f'日志可见性更新失败：{visibility_data.get("msg") if visibility_data else visibility_err}')
                    clear_problem_cache()
                    toast_safe('题目已保存', 'ok')
                    st.rerun()
                st.error(f'保存失败：{save_data.get("msg") if save_data else save_err}')

        if delete_clicked:
            delete_code, delete_data, delete_err = api('DELETE', f"/api/problems/{problem['id']}")
            if delete_code == 200:
                clear_problem_cache()
                toast_safe('题目已删除', 'ok')
                render_home_button()
                st.stop()
            st.error(f'删除失败：{delete_data.get("msg") if delete_data else delete_err}')
