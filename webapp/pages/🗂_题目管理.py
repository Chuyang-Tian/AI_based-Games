# -*- coding: utf-8 -*-
"""题目管理/题库浏览页。"""

import json
import math
import os
import sys

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


def render_problem_badges(problem, active_tags):
    diff_cls = {
        '简单': 'oj-diff-easy',
        '中等': 'oj-diff-medium',
        '困难': 'oj-diff-hard',
    }.get(problem.get('difficulty'), '')
    html_parts = [
        f'<span class="oj-pill {diff_cls}">{problem.get("difficulty") or "未标注"}</span>',
        f'<span class="oj-pill">TL {problem.get("time_limit") or "-"}s</span>',
        f'<span class="oj-pill">ML {problem.get("memory_limit") or "-"}MB</span>',
        f'<span class="oj-pill">作者 {problem.get("author") or "-"}</span>',
    ]
    for tag in (problem.get('tags') or [])[:6]:
        active_cls = ' oj-pill-active' if tag in active_tags else ''
        html_parts.append(f'<span class="oj-pill{active_cls}">#{tag}</span>')
    st.markdown(''.join(html_parts), unsafe_allow_html=True)


st.set_page_config(page_title='题目管理 · OJ', page_icon='🗂', layout='wide', initial_sidebar_state='collapsed')

ensure_init()
render_topbar('题库目录')
render_subheader([('🏠 判题首页', 'home'), ('🗂 题目管理' if is_admin() else '📚 题库浏览', None)], 'problems')

user = current_user()
if not user:
    require_login_error()
    st.stop()

if 'problem_filters' not in st.session_state:
    st.session_state['problem_filters'] = {
        'keyword': '',
        'difficulty': '',
        'tags': [],
        'page': 1,
        'page_size': 12,
    }

filters = st.session_state['problem_filters']
problems = load_all_problems(force=st.session_state.pop('problems_force_refresh', False))
all_tags = sorted({tag for item in problems for tag in (item.get('tags') or [])})

with st.container(border=True):
    st.subheader('题库筛选', divider=False)
    st.caption('这里是独立目录页，只负责浏览、检索和跳转。')
    c1, c2, c3, c4 = st.columns([4, 2, 4, 2])
    with c1:
        keyword = st.text_input('搜索题目', value=filters.get('keyword', ''), placeholder='输入题号、标题或关键字')
    with c2:
        difficulty = st.selectbox('难度', ['', '简单', '中等', '困难'], index=['', '简单', '中等', '困难'].index(filters.get('difficulty', '')))
    with c3:
        selected_tags = st.multiselect('标签筛选', all_tags, default=filters.get('tags', []), placeholder='按标签缩小范围')
    with c4:
        page_size = st.selectbox('每页数量', [8, 12, 20, 30], index=[8, 12, 20, 30].index(filters.get('page_size', 12)))

    quick_a, quick_b, quick_c = st.columns([1, 1, 2])
    with quick_a:
        if st.button('应用筛选', type='primary', use_container_width=True):
            st.session_state['problem_filters'] = {
                'keyword': keyword.strip(),
                'difficulty': difficulty,
                'tags': selected_tags,
                'page': 1,
                'page_size': page_size,
            }
            st.rerun()
    with quick_b:
        if st.button('重置', use_container_width=True):
            st.session_state['problem_filters'] = {
                'keyword': '',
                'difficulty': '',
                'tags': [],
                'page': 1,
                'page_size': 12,
            }
            st.rerun()
    with quick_c:
        if st.button('刷新题库', use_container_width=True):
            st.session_state['problems_force_refresh'] = True
            clear_problem_cache()
            st.rerun()

filters = st.session_state['problem_filters']
active_tags = list(filters.get('tags') or [])
filtered = get_filtered_problems(problems, filters.get('keyword', ''), filters.get('difficulty', ''), active_tags)
total_pages = max(1, math.ceil(len(filtered) / int(filters.get('page_size', 12) or 12)))
filters['page'] = min(max(1, int(filters.get('page', 1) or 1)), total_pages)
start = (filters['page'] - 1) * int(filters['page_size'])
end = start + int(filters['page_size'])
visible_items = filtered[start:end]

stats = st.columns(4)
stats[0].metric('题库总数', len(problems))
stats[1].metric('筛选结果', len(filtered))
stats[2].metric('已选标签', len(active_tags))
stats[3].metric('当前页码', f"{filters['page']} / {total_pages}")

with st.container(border=True):
    st.subheader('题目目录', divider=False)
    if active_tags:
        active_html = ''.join(f'<span class="oj-pill oj-pill-active">#{tag}</span>' for tag in active_tags)
        st.markdown(active_html, unsafe_allow_html=True)
    if not visible_items:
        st.info('没有匹配的题目，请调整搜索条件。')
    else:
        for item in visible_items:
            with st.container(border=True):
                left, mid, right = st.columns([7, 2, 2], gap='small')
                with left:
                    st.markdown(f"**{item.get('id')} · {item.get('title')}**")
                    render_problem_badges(item, active_tags)
                    summary = (item.get('description') or '').replace('\n', ' ').strip()
                    if summary:
                        st.caption(summary[:72] + ('...' if len(summary) > 72 else ''))
                with mid:
                    st.link_button('题目详情', page_url('problem_detail', id=item.get('id')), use_container_width=True)
                with right:
                    st.link_button('进入判题', page_url('judge', id=item.get('id')), type='primary', use_container_width=True)

pager_left, pager_mid, pager_right = st.columns([1, 2, 1])
with pager_left:
    if st.button('上一页', use_container_width=True, disabled=filters['page'] <= 1):
        st.session_state['problem_filters']['page'] = max(1, filters['page'] - 1)
        st.rerun()
with pager_mid:
    st.caption(f"当前显示第 {filters['page']} 页，共 {total_pages} 页，每页 {filters['page_size']} 条。")
with pager_right:
    if st.button('下一页', use_container_width=True, disabled=filters['page'] >= total_pages):
        st.session_state['problem_filters']['page'] = min(total_pages, filters['page'] + 1)
        st.rerun()

if is_admin():
    with st.expander('新增题目', expanded=False):
        with st.form('problem_create_form'):
            c1, c2, c3 = st.columns(3)
            with c1:
                problem_id = st.text_input('题目 ID')
            with c2:
                title = st.text_input('标题')
            with c3:
                difficulty_text = st.selectbox('难度', ['简单', '中等', '困难'], index=1)
            description = st.text_area('题目描述', height=120)
            input_description = st.text_area('输入描述', height=90)
            output_description = st.text_area('输出描述', height=90)
            constraints = st.text_area('数据范围', height=70)
            hint = st.text_area('提示', height=70)
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
            samples_text = st.text_area('样例 JSON', value=json.dumps([{'input': '', 'output': ''}], ensure_ascii=False, indent=2), height=140)
            testcases_text = st.text_area('测试点 JSON', value=json.dumps([{'input': '', 'output': ''}], ensure_ascii=False, indent=2), height=140)
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
