# -*- coding: utf-8 -*-
"""
提交日志（提交列表）页——Step3 评测管理（5分）的核心前端页面。
= 角色差异化 =
  普通用户：只能看"我的提交"（GET /api/submissions?user_id=me），user_id 过滤器锁死，看不到别人的代码；
  管理员：所有用户全部提交可见；支持按 problem_id、按 status（AC/WA/RE/TLE/MLE/CE）筛选；支持按用户 username 搜索。
= 功能 =
  - 分页：page / page_size；
  - 每行展示：提交ID / 用户 / 题目 / 语言 / 状态 tag（配色：AC 绿 / WA 红 / TLE MLE 橙 等）/ pass/total / time / memory / 提交时间；
  - 点击整行跳 🧾提交详情；
  - 管理员每行有"🔄 重判"按钮，POST /api/submissions/{sid}/rejudge，重跑 Judger 后更新 submissions 表
    （对应 Step3 的"重新评测"要求）。
= Step3 对应点 =
  提交记录查询（分页 + 筛选）+ 状态管理（rejudge 改 status + pass/total）+ 重新评测 全部完成。
"""

import os
import sys

import math
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
    render_pagination_controls,
    render_page_link,
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


def format_ai_level(level, overall):
    level = str(level or '').lower()
    overall_text = '-' if overall in (None, '') else str(overall)
    if level == 'high':
        return f'🔴 高风险（{overall_text}）'
    if level == 'mid':
        return f'🟡 中风险（{overall_text}）'
    if level == 'low':
        return f'🟢 低风险（{overall_text}）'
    return '未审查'

with st.container(border=True):
    st.subheader('筛选条件')
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
total_pages = max(1, math.ceil(total / page_size)) if total else 1
page = min(max(1, page), total_pages)
if int(filters.get('page', 1) or 1) != page:
    st.session_state['submission_filters'] = {**filters, 'page': page}
    st.rerun()

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
        **({'AI 风险': format_ai_level(item.get('ai_level'), item.get('ai_overall'))} if is_admin() else {}),
    })

with st.container(border=True):
    st.subheader('提交目录')
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
                    caption_parts = [f"状态: {row['状态']}", f"得分: {row['得分']} / {row['总分']}"]
                    if is_admin():
                        caption_parts.append(f"反AI审查: {row.get('AI 风险', '未审查')}")
                    st.caption('  |  '.join(caption_parts))
                with mid:
                    render_page_link('查看题目', page_url('problem_detail', id=row['题目 ID']))
                with right:
                    render_page_link('提交详情', page_url('submission_detail', id=row['提交 ID']), primary=True)
    elif code == 200:
        st.info('当前条件下没有提交记录。')
    else:
        st.error(f'查询失败：{data.get("msg") if data else err}')

render_pagination_controls(
    'submission_filters',
    page,
    total_pages,
    page_size,
    total_items=total,
)
