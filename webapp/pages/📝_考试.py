"""
考试页面——教学扩展功能（比作业多了"考试窗口"与"防作弊/时间锁"逻辑）。
= URL 参数 =
  ?id=xxx        exam_id，可选。
= 和作业的不同点（答辩时提一下）=
  1. 有明确的「考试起止时间」exam_window（start_time / end_time），不在窗口内不能「开始考试」；
  2. 学生点击「开始考试」POST /api/exams/{id}/start → 后端记录 exam_window_started_at，
     超时未交或过 end_time 自动交卷；
  3. 防舞弊：考试进行中 禁止查看历史提交（除自己的）+ 日志明细默认 hidden，仅管理员考完后可查；
  4. 题目列表每题限时单独做，或整体限时按个人配置。
= 功能 =
  - 管理员：创建考试、绑定班级、配置题目顺序、开/关考试窗口；
  - 学生：在考试窗口内「开始考试 → 按顺序做题 → 交卷 → 查看得分统计」。
= 设计思路 =
  与 Assignment 架构类似，只是多了 exam_window / exam_start / exam_end 三张辅助表记录状态，
  复用 Step3 submissions 表，只是多填 exam_id 字段。
"""
import os
import sys
import streamlit as st
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import api, current_user, ensure_init, is_admin, page_url, render_home_button, render_page_link, render_subheader, render_topbar, require_login_error, toast_safe
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
        st.error(f"考试加载失败：{(data.get('msg') if isinstance(data, dict) else err)}")
        render_home_button()
        st.stop()
    with st.container(border=True):
        left, mid, right = st.columns([5, 2, 2])
        with left:
            st.subheader(detail.get('title', ''))
            st.caption(detail.get('description') or '暂无考试说明')
        with mid:
            if not is_admin() and st.button('开始考试', use_container_width=True, type='primary'):
                start_code, start_data, start_err = api('POST', f'/api/exams/{exam_id}/start')
                if start_code == 200:
                    toast_safe('考试已开始', 'ok')
                    st.rerun()
                st.error(f"开始失败：{(start_data.get('msg') if start_data else start_err)}")
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
                    title_text = item.get('title') or pid or '未命名题目'
                    order_value = item.get('order') or item.get('order_index') or '-'
                    st.markdown(f'**{pid} · {title_text}**')
                    st.caption(f"分值：{item.get('points', 0)}  |  顺序：{order_value}")
                with mid:
                    render_page_link('题目详情', page_url('problem_detail', id=pid))
                with right:
                    render_page_link('进入做题', page_url('judge', id=pid, exam_id=exam_id), primary=True)
    if is_admin():
        with st.expander('考试管理', expanded=False):
            publish_now = st.checkbox('立即发布成绩', value=bool(detail.get('score_published')))
            if st.button('更新成绩发布状态', type='primary', use_container_width=True):
                publish_code, publish_data, publish_err = api('PUT', f'/api/exams/{exam_id}/publish', {'score_published': publish_now})
                if publish_code == 200:
                    toast_safe('考试发布状态已更新', 'ok')
                    st.rerun()
                st.error(f"更新失败：{(publish_data.get('msg') if publish_data else publish_err)}")
            stats_code, stats_data, stats_err = api('GET', f'/api/exams/{exam_id}/stats')
            if stats_code == 200 and isinstance(stats_data, dict):
                stats = stats_data.get('data') or {}
                s1, s2, s3 = st.columns(3)
                s1.metric('参与人数', len(stats.get('rows') or []))
                s2.metric('事件日志', len(stats.get('events') or []))
                s3.metric('题目数量', len(stats.get('problems') or []))
            else:
                st.caption(f"统计暂不可用：{(stats_data.get('msg') if stats_data else stats_err)}")
else:
    render_subheader([('🏠 判题首页', 'home'), ('📝 考试', None)], 'exams')
    code, data, err = api('GET', '/api/exams')
    exams = data.get('data') if code == 200 and isinstance(data, dict) else []
    with st.container(border=True):
        left, right = st.columns([6, 2])
        with left:
            st.subheader('考试列表')
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
    if is_admin():
        classes_code, classes_data, _ = api('GET', '/api/classes')
        classes = classes_data.get('data') if classes_code == 200 and isinstance(classes_data, dict) else []
        probs_code, probs_data, _ = api('GET', '/api/problems')
        problems = probs_data.get('data') if probs_code == 200 and isinstance(probs_data, dict) else []
        class_options = {f"#{item.get('class_id')} · {item.get('class_name')}": int(item.get('class_id')) for item in classes or []}
        problem_options = {f"{item.get('id')} · {item.get('title') or item.get('id')}": str(item.get('id')) for item in problems or []}
        with st.expander('创建考试', expanded=False):
            with st.form('exam_create_form'):
                title = st.text_input('考试标题')
                description = st.text_area('考试说明', height=100)
                selected_classes = st.multiselect('面向班级', list(class_options.keys()))
                selected_problems = st.multiselect('题目列表', list(problem_options.keys()))
                point_each = st.number_input('每题分值', min_value=1, max_value=100, value=50, step=5)
                mode = st.selectbox('考试模式', options=[1, 2], format_func=lambda x: '固定窗口' if x == 1 else '个人计时')
                duration_minutes = st.number_input('个人计时时长（分钟）', min_value=1, max_value=480, value=90, step=5)
                start_at = st.text_input('开始时间', value='2020-01-01 00:00:00')
                end_at = st.text_input('结束时间', value='2099-12-31 23:59:59')
                score_published = st.checkbox('创建后立即发布成绩', value=False)
                created = st.form_submit_button('创建考试', type='primary', use_container_width=True)
            if created:
                payload = {'title': title.strip(), 'description': description, 'mode': int(mode), 'duration_minutes': int(duration_minutes), 'audience_classes': [class_options[key] for key in selected_classes], 'problem_order': [{'problem_id': problem_options[key], 'points': int(point_each), 'order': idx + 1} for idx, key in enumerate(selected_problems)], 'start_at': start_at.strip() or None, 'end_at': end_at.strip() or None, 'score_published': score_published}
                create_code, create_data, create_err = api('POST', '/api/exams', payload)
                if create_code == 200:
                    toast_safe('考试创建成功', 'ok')
                    st.rerun()
                st.error(f"创建失败：{(create_data.get('msg') if create_data else create_err)}")