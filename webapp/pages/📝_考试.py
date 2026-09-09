# -*- coding: utf-8 -*-
"""
📝 考试中心（route_key=exams，teacher/admin 管理，学生进入自己考试）
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
st.set_page_config(page_title='考试中心 - OJ', page_icon='📝', layout='wide',
                   initial_sidebar_state='collapsed')

from common import (
    ensure_init, render_topbar, render_subheader,
    current_user, require_login_error, is_admin, is_teacher,
    api, toast_safe, goto, load_all_problems,
)

ensure_init()
render_topbar('考试中心')
render_subheader([
    ('🏠 判题首页', 'home'),
    ('📝 考试', None),
], 'exams')
user = current_user()

if not user:
    require_login_error()
    st.stop()

import pandas as pd
from datetime import datetime, timedelta

def load_classes():
    c, d, _ = api('GET', '/api/classes/')
    if c == 200 and isinstance(d, dict):
        data = d.get('data')
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get('list') or data.get('items') or []
    return []

def load_exams():
    c, d, _ = api('GET', '/api/exams/')
    if c == 200 and isinstance(d, dict):
        data = d.get('data')
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get('list') or data.get('items') or []
    return []

all_exams = load_exams()
all_classes = load_classes()
all_problems = load_all_problems()

problem_options = [(p.get('id'), f"{p.get('id')} - {p.get('title')}") for p in all_problems]
problem_ids_list = [str(po[0]) for po in problem_options]
problem_labels_list = [po[1] for po in problem_options]

class_options = [(c.get('id'), c.get('name') or str(c.get('id'))) for c in all_classes]
class_ids_list = [str(co[0]) for co in class_options]
class_labels_list = [co[1] for co in class_options]

can_manage = is_admin() or is_teacher()

if can_manage:
    with st.container(border=True):
        st.subheader('➕ 新建考试')
        with st.form('exam_add_form'):
            a, b = st.columns(2)
            with a:
                ne_title = st.text_input('考试标题 *')
                ne_class_idx = 0
                ne_class_label = st.selectbox('所属班级', class_labels_list if class_labels_list else ['-'], index=ne_class_idx)
                ne_start = st.text_input('开始时间（ISO 格式，如 2026-03-20T14:00:00）', value='')
                ne_end = st.text_input('结束时间（ISO 格式，如 2026-03-20T16:00:00）', value='')
                ne_duration = st.number_input('总时长（分钟）', min_value=10, max_value=720, step=10, value=120)
            with b:
                ne_problem_indices = st.multiselect(
                    '选择题目（可多选）',
                    range(len(problem_labels_list)),
                    format_func=lambda i: problem_labels_list[i] if i < len(problem_labels_list) else '',
                )
                ne_is_public = st.checkbox('公开给学生可见', value=True)
                ne_anti_cheat = st.checkbox('启用 AI 防作弊检测', value=True)
            if st.form_submit_button('✅ 创建考试', type='primary', use_container_width=True):
                if not ne_title:
                    st.error('考试标题为必填项')
                else:
                    class_id = None
                    if class_options and ne_class_label in class_labels_list:
                        idx = class_labels_list.index(ne_class_label)
                        class_id = class_options[idx][0]
                    selected_pids = [problem_ids_list[i] for i in ne_problem_indices if i < len(problem_ids_list)]
                    payload = {
                        'title': ne_title,
                        'class_id': class_id,
                        'start_time': ne_start or None,
                        'end_time': ne_end or None,
                        'duration_minutes': int(ne_duration),
                        'problem_ids': selected_pids,
                        'is_public': bool(ne_is_public),
                        'anti_cheat': bool(ne_anti_cheat),
                    }
                    c2, d2, err = api('POST', '/api/exams/', payload)
                    if c2 == 200:
                        toast_safe('考试创建成功', 'ok')
                        st.rerun()
                    else:
                        st.error(f'创建失败：{d2.get("msg") if d2 else err}')

tab_exams, tab_detail = st.tabs(['📋 考试列表', '📂 考试详情'])

with tab_exams:
    def get_exam_status(e):
        now = datetime.now()
        start_str = str(e.get('start_time') or '')
        end_str = str(e.get('end_time') or '')
        try:
            start_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00')) if start_str else None
            end_dt = datetime.fromisoformat(end_str.replace('Z', '+00:00')) if end_str else None
        except Exception:
            start_dt, end_dt = None, None
        if start_dt and now < start_dt:
            return '⏳ 未开始'
        if end_dt and now > end_dt:
            return '✅ 已结束'
        return '🔄 进行中'

    if can_manage:
        visible_exams = all_exams
    else:
        user_class_id = str(user.get('class_id') or '')
        visible_exams = [e for e in all_exams
                         if (str(e.get('class_id')) == user_class_id or not e.get('class_id'))
                         and (e.get('is_public', True) or True)]

    if not visible_exams:
        st.info('（暂无可见考试）')
    else:
        erows = []
        for e in visible_exams:
            pids = e.get('problem_ids') or []
            erows.append({
                'ID': e.get('id') or '',
                '标题': e.get('title') or '',
                '状态': get_exam_status(e),
                '题目数': len(pids) or e.get('problem_count') or 0,
                '时长(分)': e.get('duration_minutes') or '-',
                '班级': next((c.get('name') for c in all_classes if str(c.get('id')) == str(e.get('class_id'))), '-') or e.get('class_name') or '-',
                '开始时间': str(e.get('start_time') or '-'),
                '结束时间': str(e.get('end_time') or '-'),
            })
        st.dataframe(pd.DataFrame(erows), use_container_width=True, hide_index=True)

with tab_detail:
    exam_ids = [str(r['ID']) for r in erows if r['ID']] if 'erows' in dir() else []
    if not exam_ids:
        st.info('（请先在上方「考试列表」Tab 中选择一个考试）')
    else:
        selected_eid = st.selectbox('选择考试 ID', exam_ids, key='detail_exam_select')
        selected_exam = next((e for e in visible_exams if str(e.get('id')) == selected_eid), None)

        if selected_exam:
            with st.container(border=True):
                st.subheader(f'📂 {selected_exam.get("title") or selected_eid}')
                pids = selected_exam.get('problem_ids') or []
                duration = int(selected_exam.get('duration_minutes') or 120)
                start_str = str(selected_exam.get('start_time') or '')
                end_str = str(selected_exam.get('end_time') or '')

                now = datetime.now()
                try:
                    start_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00')) if start_str else None
                    end_dt = datetime.fromisoformat(end_str.replace('Z', '+00:00')) if end_str else (start_dt + timedelta(minutes=duration) if start_dt else None)
                except Exception:
                    start_dt, end_dt = None, None

                countdown_placeholder = st.empty()
                progress_placeholder = st.empty()

                if start_dt and end_dt and now >= start_dt and now <= end_dt:
                    remaining = end_dt - now
                    total_seconds = int(remaining.total_seconds())
                    total_duration = (end_dt - start_dt).total_seconds()
                    elapsed = total_duration - total_seconds
                    pct = min(100.0, (elapsed / total_duration * 100.0) if total_duration > 0 else 0)

                    hours, rem = divmod(total_seconds, 3600)
                    minutes, seconds = divmod(rem, 60)
                    countdown_placeholder.metric('⏰ 剩余时间', f'{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}')
                    progress_placeholder.progress(pct / 100.0, text=f'考试进行中... {pct:.1f}%')
                elif start_dt and now < start_dt:
                    countdown_placeholder.caption(f'⏳ 考试未开始，开始时间：{start_str}')
                    progress_placeholder.progress(0.0, text='尚未开始')
                elif end_dt and now > end_dt:
                    countdown_placeholder.caption(f'✅ 考试已结束，结束时间：{end_str}')
                    progress_placeholder.progress(1.0, text='已结束')
                else:
                    countdown_placeholder.caption('ℹ️ 未设置时间限制')
                    progress_placeholder.progress(0.0)

            with st.container(border=True):
                st.subheader('📝 题目列表')
                m1, m2 = st.columns(2)
                m1.metric('📋 总题数', len(pids))

                for idx, pid in enumerate(pids):
                    p = next((pp for pp in all_problems if str(pp.get('id')) == str(pid)), None)
                    title = p.get('title') if p else str(pid)
                    difficulty = p.get('difficulty') if p else '-'
                    tags = ', '.join((p.get('tags') or [])) if p else '-'

                    col1, col2, col3 = st.columns([1, 6, 2])
                    with col1:
                        st.markdown(f'### {idx+1}')
                    with col2:
                        st.write(f'**题目 ID：** `{pid}`')
                        st.write(f'**标题：** {title}')
                        if difficulty != '-':
                            st.caption(f'难度：{difficulty} ｜ 标签：{tags}')
                    with col3:
                        st.button('➜ 开始做题', key=f'go_judge_exam_{selected_eid}_{idx}',
                                 on_click=goto,
                                 kwargs=dict(route_key='judge', id=str(pid), exam=str(selected_eid), _from='exam'),
                                 use_container_width=True, type='primary')

st.caption('© OJ 在线判题平台 · Streamlit 前端 + FastAPI 后端（Python 双栈架构）')
