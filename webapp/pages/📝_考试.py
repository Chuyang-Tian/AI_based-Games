# -*- coding: utf-8 -*-
"""考试页面。"""

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import (
    api,
    current_user,
    ensure_init,
    is_admin,
    page_url,
    render_home_button,
    render_page_link,
    render_subheader,
    render_topbar,
    require_login_error,
    toast_safe,
)

st.set_page_config(page_title='考试 · OJ', page_icon='📝', layout='wide', initial_sidebar_state='collapsed')

ensure_init()
render_topbar('考试系统')

user = current_user()
if not user:
    require_login_error()
    st.stop()

raw_exam_id = st.query_params.get('id') or ''
exam_id = str(raw_exam_id[0]) if isinstance(raw_exam_id, list) and raw_exam_id else str(raw_exam_id or '')

if exam_id:
    render_subheader([('🏠 判题首页', 'home'), ('📝 考试', 'exams'), (f'考试 #{exam_id}', None)], 'exams')
    code, data, err = api('GET', f'/api/exams/{exam_id}')
    detail = data.get('data') if code == 200 and isinstance(data, dict) else None
    win_code, win_data, _ = api('GET', f'/api/exams/{exam_id}/window')
    exam_window = win_data.get('data') if win_code == 200 and isinstance(win_data, dict) else {}
    if not detail:
        st.error(f'考试加载失败：{data.get("msg") if isinstance(data, dict) else err}')
        render_home_button()
        st.stop()

    with st.container(border=True):
        left, mid, right = st.columns([5, 2, 2])
        with left:
            st.subheader(detail.get('title', ''), divider=False)
            st.caption(detail.get('description') or '暂无考试说明')
        with mid:
            if not is_admin() and st.button('开始考试', use_container_width=True, type='primary'):
                start_code, start_data, start_err = api('POST', f'/api/exams/{exam_id}/start')
                if start_code == 200:
                    toast_safe('考试已开始', 'ok')
                    st.rerun()
                st.error(f'开始失败：{start_data.get("msg") if start_data else start_err}')
        with right:
            render_home_button()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric('考试模式', '固定窗口' if int(detail.get('mode', 1) or 1) == 1 else '个人计时')
        m2.metric('题目数量', detail.get('problem_count', 0))
        m3.metric('总分', detail.get('total_points', 0))
        m4.metric('成绩发布', '已发布' if detail.get('score_published') else '未发布')

    if exam_window:
        with st.container(border=True):
            st.markdown('**考试时间窗口**')
            st.caption(f"开始：{exam_window.get('start_at') or detail.get('start_at') or '-'}  |  结束：{exam_window.get('end_at') or detail.get('end_at') or '-'}")

    st.markdown('#### 题目列表')
    problems = detail.get('problem_order') or []
    if not problems:
        st.info('该考试暂无题目')
    else:
        for item in problems:
            pid = item.get('problem_id')
            with st.container(border=True):
                left, mid, right = st.columns([6, 2, 2])
                with left:
                    st.markdown(f"**{pid} · {item.get('title') or ''}**")
                    st.caption(f"分值：{item.get('points', 0)}  |  顺序：{item.get('order_index', 0)}")
                with mid:
                    render_page_link('题目详情', page_url('problem_detail', id=pid))
                with right:
                    render_page_link('进入做题', page_url('judge', id=pid, exam_id=exam_id), primary=True)

    if is_admin():
        with st.expander('考试管理', expanded=False):
            stats_code, stats_data, stats_err = api('GET', f'/api/exams/{exam_id}/stats')
            if stats_code == 200 and isinstance(stats_data, dict):
                stats = stats_data.get('data') or {}
                s1, s2, s3 = st.columns(3)
                s1.metric('参与人数', len(stats.get('rows') or []))
                s2.metric('事件日志', len(stats.get('events') or []))
                s3.metric('题目数量', len((stats.get('problems') or [])))
            else:
                st.caption(f'统计暂不可用：{stats_data.get("msg") if stats_data else stats_err}')
else:
    render_subheader([('🏠 判题首页', 'home'), ('📝 考试', None)], 'exams')
    code, data, err = api('GET', '/api/exams')
    exams = data.get('data') if code == 200 and isinstance(data, dict) else []

    with st.container(border=True):
        left, right = st.columns([6, 2])
        with left:
            st.subheader('考试列表', divider=False)
            st.caption('考试创新功能已经恢复，支持查看考试详情并带上下文进入做题页。')
        with right:
            render_home_button()

    if not exams:
        st.info('暂无考试数据')
    else:
        for item in exams:
            with st.container(border=True):
                left, right = st.columns([7, 2])
                with left:
                    mode_text = '固定窗口' if int(item.get('mode', 1) or 1) == 1 else f"个人计时 {item.get('duration_minutes', 0)} 分钟"
                    st.markdown(f"**考试 #{item.get('exam_id')} · {item.get('title')}**")
                    st.caption(f"{mode_text}  |  题目数：{item.get('problem_count')}  |  结束：{item.get('end_at') or '-'}")
                with right:
                    render_page_link('查看考试', page_url('exams', id=item.get('exam_id')), primary=True)
