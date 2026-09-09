# -*- coding: utf-8 -*-
"""OJ 首页概览。"""

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import api, current_user, ensure_init, is_admin, page_url, render_page_link, render_subheader, render_topbar

st.set_page_config(page_title='判题首页 · OJ', page_icon='🏠', layout='wide', initial_sidebar_state='collapsed')


def fetch_list(path):
    code, data, _ = api('GET', path)
    if code == 200 and isinstance(data, dict) and isinstance(data.get('data'), list):
        return data.get('data') or []
    return []


def render_preview_card(title, items, empty_text, route_key, kind):
    with st.container(border=True):
        head_left, head_right = st.columns([6, 2])
        with head_left:
            st.subheader(title, divider=False)
        with head_right:
            render_page_link('查看全部', page_url(route_key))

        if not items:
            st.info(empty_text)
            return

        for item in items[:3]:
            if kind == 'class':
                item_id = item.get('class_id')
                item_title = item.get('class_name') or '未命名班级'
                item_desc = f"成员数：{item.get('member_count', 0)}  |  {item.get('description') or '暂无简介'}"
                detail_url = page_url('classes', id=item_id)
                detail_label = '进入班级'
            elif kind == 'assignment':
                item_id = item.get('assignment_id')
                item_title = item.get('title') or '未命名作业'
                item_desc = f"题目数：{item.get('problem_count', 0)}  |  总分：{item.get('total_points', 0)}  |  截止：{item.get('due_at') or '-'}"
                detail_url = page_url('assignments', id=item_id)
                detail_label = '进入作业'
            else:
                item_id = item.get('exam_id')
                item_title = item.get('title') or '未命名考试'
                mode_text = '固定窗口' if int(item.get('mode', 1) or 1) == 1 else f"个人计时 {item.get('duration_minutes', 0)} 分钟"
                item_desc = f"{mode_text}  |  题目数：{item.get('problem_count', 0)}  |  结束：{item.get('end_at') or '-'}"
                detail_url = page_url('exams', id=item_id)
                detail_label = '进入考试'

            row_left, row_right = st.columns([6, 2])
            with row_left:
                st.markdown(f'**#{item_id} · {item_title}**')
                st.caption(item_desc)
            with row_right:
                render_page_link(detail_label, detail_url)


ensure_init()
user = current_user()

render_topbar('首页概览')
render_subheader([('🏠 判题首页', None)], 'home')

classes = fetch_list('/api/classes') if user else []
assignments = fetch_list('/api/assignments') if user else []
exams = fetch_list('/api/exams') if user else []

with st.container(border=True):
    top_left, top_right = st.columns([7, 3])
    with top_left:
        st.subheader('欢迎来到 OJ 调试平台', divider=False)
        if user:
            role_text = '管理员' if is_admin() else '普通用户'
            st.caption(f'当前登录：{user.get("username", "")}（{role_text}）')
        else:
            st.caption('登录后可查看班级、作业、考试和个人提交信息。')
    with top_right:
        render_page_link('进入题库浏览', page_url('problems'), primary=True)
        render_page_link('查看提交记录', page_url('submissions'))

    m1, m2, m3, m4 = st.columns(4)
    m1.metric('班级', len(classes))
    m2.metric('作业', len(assignments))
    m3.metric('考试', len(exams))
    m4.metric('身份', '管理员' if is_admin() else ('已登录' if user else '未登录'))

col1, col2, col3 = st.columns(3, gap='large')
with col1:
    render_preview_card(
        '班级概览',
        classes,
        '暂无班级数据',
        'classes',
        'class',
    )
with col2:
    render_preview_card(
        '作业概览',
        assignments,
        '暂无作业数据',
        'assignments',
        'assignment',
    )
with col3:
    render_preview_card(
        '考试概览',
        exams,
        '暂无考试数据',
        'exams',
        'exam',
    )

if not user:
    st.info('请先点击右上角“登录 / 注册”，登录后即可查看班级、作业、考试以及个人提交信息。')
