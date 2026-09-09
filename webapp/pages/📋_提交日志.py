# -*- coding: utf-8 -*-
"""提交日志页。"""

import os
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import (
    api,
    current_user,
    ensure_init,
    is_admin,
    load_all_problems,
    page_url,
    render_subheader,
    render_topbar,
    require_login_error,
)

st.set_page_config(page_title='提交日志 · OJ', page_icon='📋', layout='wide', initial_sidebar_state='collapsed')

ensure_init()
render_topbar('提交记录目录页')
render_subheader([('🏠 判题首页', 'home'), ('📋 提交日志', None)], 'submissions')

user = current_user()
if not user:
    require_login_error()
    st.stop()

problems = load_all_problems()
problem_title_map = {item.get('id'): item.get('title') for item in problems}

filters = st.session_state.get('submission_filters', {
    'problem_id': '',
    'status': '',
    'user_id': str(user.get('user_id', '')),
    'page': 1,
    'page_size': 20,
})

with st.container(border=True):
    st.subheader('筛选条件', divider=False)
    with st.form('submission_filter_form'):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            problem_id = st.text_input('题目 ID', value=filters.get('problem_id', ''))
        with c2:
            status = st.selectbox('状态', ['', 'pending', 'success', 'error', 'AC', 'WA', 'TLE', 'MLE', 'RE', 'CE'])
        with c3:
            user_id = st.text_input('用户 ID', value=filters.get('user_id', ''), disabled=not is_admin())
        with c4:
            page_size = st.selectbox('每页数量', [10, 20, 50], index=[10, 20, 50].index(int(filters.get('page_size', 20))))
        submit = st.form_submit_button('查询', type='primary', use_container_width=True)
    if submit:
        st.session_state['submission_filters'] = {
            'problem_id': problem_id.strip(),
            'status': status,
            'user_id': user_id.strip() if is_admin() else str(user.get('user_id', '')),
            'page': 1,
            'page_size': page_size,
        }
        st.rerun()

filters = st.session_state.get('submission_filters', filters)
page = int(filters.get('page', 1) or 1)
page_size = int(filters.get('page_size', 20) or 20)
params = {'page': page, 'page_size': page_size}
if filters.get('problem_id'):
    params['problem_id'] = filters['problem_id']
if filters.get('status'):
    params['status'] = filters['status']
if filters.get('user_id'):
    params['user_id'] = filters['user_id'] if is_admin() else str(user.get('user_id', ''))

code, data, err = api('GET', '/api/submissions/', params=params)
payload = data.get('data') if isinstance(data, dict) else {}
submissions = payload.get('submissions') if isinstance(payload, dict) else []
total = int(payload.get('total', 0) or 0) if isinstance(payload, dict) else 0

rows = []
for item in submissions or []:
    sid = item.get('submission_id') or item.get('id')
    pid = item.get('problem_id', '')
    rows.append({
        '提交 ID': sid,
        '题目 ID': pid,
        '题目标题': problem_title_map.get(pid, pid),
        '状态': item.get('status', ''),
        '得分': item.get('score'),
        '总分': item.get('counts'),
    })

with st.container(border=True):
    st.subheader('提交目录', divider=False)
    st.caption('这里仅展示目录与筛选；详细信息进入独立提交详情页。')
    stats = st.columns(4)
    stats[0].metric('当前页记录数', len(rows))
    stats[1].metric('查询总数', total)
    stats[2].metric('成功数', sum(1 for row in rows if str(row['状态']).lower() in ('success', 'ac')))
    stats[3].metric('待评测数', sum(1 for row in rows if str(row['状态']).lower() == 'pending'))
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        for row in rows:
            with st.container(border=True):
                left, mid, right = st.columns([6, 2, 2])
                with left:
                    st.markdown(f"**提交 #{row['提交 ID']} · {row['题目 ID']} · {row['题目标题']}**")
                    st.caption(f"状态: {row['状态']}  |  得分: {row['得分']} / {row['总分']}")
                with mid:
                    st.link_button('查看题目', page_url('problem_detail', id=row['题目 ID']), use_container_width=True)
                with right:
                    st.link_button('提交详情', page_url('submission_detail', id=row['提交 ID']), type='primary', use_container_width=True)
    elif code == 200:
        st.info('当前条件下没有提交记录。')
    else:
        st.error(f'查询失败：{data.get("msg") if data else err}')

pager_left, pager_right, pager_info = st.columns([2, 2, 6])
with pager_left:
    if st.button('上一页', use_container_width=True, disabled=page <= 1):
        st.session_state['submission_filters']['page'] = max(1, page - 1)
        st.rerun()
with pager_right:
    if st.button('下一页', use_container_width=True, disabled=page * page_size >= total):
        st.session_state['submission_filters']['page'] = page + 1
        st.rerun()
with pager_info:
    st.caption(f'当前第 {page} 页，每页 {page_size} 条。')
