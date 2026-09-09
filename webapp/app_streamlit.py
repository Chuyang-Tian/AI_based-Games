# -*- coding: utf-8 -*-
"""OJ 首页概览。"""

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import api, current_user, ensure_init, is_admin, page_url, render_page_link, render_subheader, render_topbar, get_locale, OJ_VERSION

st.set_page_config(page_title='判题首页 · OJ', page_icon='🏠', layout='wide', initial_sidebar_state='collapsed')


def t(zh: str, en: str) -> str:
    return en if get_locale() == 'en-US' else zh


def fetch_list(path):
    code, data, _ = api('GET', path)
    if code == 200 and isinstance(data, dict) and isinstance(data.get('data'), list):
        return data.get('data') or []
    return []


def render_preview_card(title, items, empty_text, route_key, kind):
    with st.container(border=True):
        head_left, head_right = st.columns([6, 2])
        with head_left:
            st.subheader(title)
        with head_right:
            render_page_link(t('查看全部', 'View All'), page_url(route_key))

        if not items:
            st.info(empty_text)
            return

        for item in items[:3]:
            if kind == 'class':
                item_id = item.get('class_id')
                item_title = item.get('class_name') or t('未命名班级', 'Untitled Class')
                item_desc = t('成员数', 'Members') + f"：{item.get('member_count', 0)}  |  {item.get('description') or t('暂无简介', 'No description')}"
                detail_url = page_url('classes', id=item_id)
                detail_label = t('进入班级', 'Open Class')
            elif kind == 'assignment':
                item_id = item.get('assignment_id')
                item_title = item.get('title') or t('未命名作业', 'Untitled Assignment')
                item_desc = t('题目数', 'Problems') + f"：{item.get('problem_count', 0)}  |  " + t('总分', 'Points') + f"：{item.get('total_points', 0)}  |  " + t('截止', 'Due') + f"：{item.get('due_at') or '-'}"
                detail_url = page_url('assignments', id=item_id)
                detail_label = t('进入作业', 'Open Assignment')
            else:
                item_id = item.get('exam_id')
                item_title = item.get('title') or t('未命名考试', 'Untitled Exam')
                mode_text = t('固定窗口', 'Fixed Window') if int(item.get('mode', 1) or 1) == 1 else t('个人计时', 'Personal Timer') + f" {item.get('duration_minutes', 0)} " + t('分钟', 'min')
                item_desc = f"{mode_text}  |  " + t('题目数', 'Problems') + f"：{item.get('problem_count', 0)}  |  " + t('结束', 'Ends') + f"：{item.get('end_at') or '-'}"
                detail_url = page_url('exams', id=item_id)
                detail_label = t('进入考试', 'Open Exam')

            row_left, row_right = st.columns([6, 2])
            with row_left:
                st.markdown(f'**#{item_id} · {item_title}**')
                st.caption(item_desc)
            with row_right:
                render_page_link(detail_label, detail_url)


ensure_init()
user = current_user()

render_topbar(t('首页概览', 'Home Overview'))
render_subheader([(t('🏠 判题首页', '🏠 Home'), None)], 'home')

classes = fetch_list('/api/classes') if user else []
assignments = fetch_list('/api/assignments') if user else []
exams = fetch_list('/api/exams') if user else []

with st.container(border=True):
    top_left, top_right = st.columns([7, 3])
    with top_left:
        st.markdown(
            f'<h3 style="margin:0;padding:0;">欢迎来到 OJ 调试平台  <span style="color:#9ca3af;font-size:14px;font-weight:400;">（{OJ_VERSION}）</span></h3>',
            unsafe_allow_html=True,
        )
        if user:
            role_text = t('管理员', 'Admin') if is_admin() else t('普通用户', 'User')
            st.caption(t(f'当前登录：{user.get("username", "")}（{role_text}）', f'Current user: {user.get("username", "")} ({role_text})'))
        else:
            st.caption(t('登录后可查看班级、作业、考试和个人提交信息。', 'Log in to view classes, assignments, exams, and your submissions.'))
    with top_right:
        render_page_link(t('进入题库浏览', 'Open Problemset'), page_url('problems'), primary=True)
        render_page_link(t('查看提交记录', 'Open Submissions'), page_url('submissions'))

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(t('班级', 'Classes'), len(classes))
    m2.metric(t('作业', 'Assignments'), len(assignments))
    m3.metric(t('考试', 'Exams'), len(exams))
    m4.metric(t('身份', 'Role'), t('管理员', 'Admin') if is_admin() else (t('已登录', 'Logged In') if user else t('未登录', 'Guest')))

col1, col2, col3 = st.columns(3, gap='large')
with col1:
    render_preview_card(
        t('班级概览', 'Class Overview'),
        classes,
        t('暂无班级数据', 'No class data'),
        'classes',
        'class',
    )
with col2:
    render_preview_card(
        t('作业概览', 'Assignment Overview'),
        assignments,
        t('暂无作业数据', 'No assignment data'),
        'assignments',
        'assignment',
    )
with col3:
    render_preview_card(
        t('考试概览', 'Exam Overview'),
        exams,
        t('暂无考试数据', 'No exam data'),
        'exams',
        'exam',
    )

if not user:
    st.info(t('请先点击右上角“登录 / 注册”，登录后即可查看班级、作业、考试以及个人提交信息。', 'Click "Login / Sign Up" in the top-right corner to view classes, assignments, exams, and your submissions.'))
