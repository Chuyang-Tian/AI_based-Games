# -*- coding: utf-8 -*-
"""
📚 作业中心（route_key=assignments，teacher/admin 新建，学生看自己班级作业）
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
st.set_page_config(page_title='作业中心 - OJ', page_icon='📚', layout='wide',
                   initial_sidebar_state='collapsed')

from common import (
    ensure_init, render_topbar, render_subheader,
    current_user, require_login_error, is_admin, is_teacher,
    api, toast_safe, goto, load_all_problems,
)

ensure_init()
render_topbar('作业中心')
render_subheader([
    ('🏠 判题首页', 'home'),
    ('📚 作业', None),
], 'assignments')
user = current_user()

if not user:
    require_login_error()
    st.stop()

import pandas as pd
from datetime import datetime

def load_classes():
    c, d, _ = api('GET', '/api/classes/')
    if c == 200 and isinstance(d, dict):
        data = d.get('data')
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get('list') or data.get('items') or []
    return []

def load_assignments():
    c, d, _ = api('GET', '/api/assignments/')
    if c == 200 and isinstance(d, dict):
        data = d.get('data')
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get('list') or data.get('items') or []
    return []

def load_my_submissions(uid):
    c, d, _ = api('GET', '/api/submissions/', params={'user_id': uid})
    if c == 200 and isinstance(d, dict):
        data = d.get('data')
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get('list') or data.get('submissions') or data.get('items') or []
    return []

all_assignments = load_assignments()
all_classes = load_classes()
all_problems = load_all_problems()

problem_options = [(p.get('id'), f"{p.get('id')} - {p.get('title')}") for p in all_problems]
problem_ids_list = [str(po[0]) for po in problem_options]
problem_labels_list = [po[1] for po in problem_options]

class_options = [(c.get('id'), c.get('name') or str(c.get('id'))) for c in all_classes]
class_ids_list = [str(co[0]) for co in class_options]
class_labels_list = [co[1] for co in class_options]

can_create = is_admin() or is_teacher()

if can_create:
    with st.container(border=True):
        st.subheader('➕ 新建作业')
        with st.form('as_add_form'):
            a, b = st.columns(2)
            with a:
                na_title = st.text_input('作业标题 *')
                na_class_idx = 0
                na_class_label = st.selectbox('所属班级', class_labels_list if class_labels_list else ['-'], index=na_class_idx)
                na_start = st.text_input('开始时间（ISO 格式，如 2026-03-20T14:00:00）', value='')
                na_end = st.text_input('截止时间（ISO 格式，如 2026-03-27T23:59:59）', value='')
            with b:
                na_problem_indices = st.multiselect(
                    '选择题目（可多选）',
                    range(len(problem_labels_list)),
                    format_func=lambda i: problem_labels_list[i] if i < len(problem_labels_list) else '',
                )
                na_score = st.number_input('每题分值', min_value=1, max_value=100, step=1, value=10)
                na_is_public = st.checkbox('立即公开给学生', value=True)
            if st.form_submit_button('✅ 创建作业', type='primary', use_container_width=True):
                if not na_title:
                    st.error('作业标题为必填项')
                else:
                    class_id = None
                    if class_options and na_class_label in class_labels_list:
                        idx = class_labels_list.index(na_class_label)
                        class_id = class_options[idx][0]
                    selected_pids = [problem_ids_list[i] for i in na_problem_indices if i < len(problem_ids_list)]
                    payload = {
                        'title': na_title,
                        'class_id': class_id,
                        'start_time': na_start or None,
                        'end_time': na_end or None,
                        'problem_ids': selected_pids,
                        'score_per_problem': int(na_score),
                        'is_public': bool(na_is_public),
                    }
                    c2, d2, err = api('POST', '/api/assignments/', payload)
                    if c2 == 200:
                        toast_safe('作业创建成功', 'ok')
                        st.rerun()
                    else:
                        st.error(f'创建失败：{d2.get("msg") if d2 else err}')

tab_list, tab_progress = st.tabs(['📋 作业列表', '📊 我的完成情况'])

with tab_list:
    def get_assignment_status(a):
        now = datetime.now()
        start_str = str(a.get('start_time') or '')
        end_str = str(a.get('end_time') or a.get('due_date') or '')
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

    if can_create:
        visible_assigns = all_assignments
    else:
        user_class_id = str(user.get('class_id') or '')
        visible_assigns = [a for a in all_assignments
                           if (str(a.get('class_id')) == user_class_id or not a.get('class_id'))
                           and (a.get('is_public', True) or True)]

    if not visible_assigns:
        st.info('（暂无可见作业）')
    else:
        arows = []
        for a in visible_assigns:
            pids = a.get('problem_ids') or []
            arows.append({
                'ID': a.get('id') or '',
                '标题': a.get('title') or '',
                '状态': get_assignment_status(a),
                '题目数': len(pids) or a.get('problem_count') or 0,
                '班级': next((c.get('name') for c in all_classes if str(c.get('id')) == str(a.get('class_id'))), '-') or a.get('class_name') or '-',
                '开始时间': str(a.get('start_time') or '-'),
                '截止时间': str(a.get('end_time') or a.get('due_date') or '-'),
            })
        st.dataframe(pd.DataFrame(arows), use_container_width=True, hide_index=True)

    assign_ids = [str(r['ID']) for r in arows if r['ID']]
    if assign_ids:
        with st.container(border=True):
            st.subheader('📂 作业详情')
            selected_aid = st.selectbox('选择作业 ID', assign_ids)
            selected_assign = next((a for a in visible_assigns if str(a.get('id')) == selected_aid), None)

            if selected_assign:
                pids = selected_assign.get('problem_ids') or []
                done_count = 0
                my_subs = []
                if user:
                    my_subs = load_my_submissions(user.get('id'))
                    solved_pids = set()
                    for s in my_subs:
                        if s.get('status') == 'AC' and s.get('problem_id'):
                            solved_pids.add(str(s.get('problem_id')))
                    done_count = len([pid for pid in pids if str(pid) in solved_pids])

                m1, m2 = st.columns(2)
                m1.metric('📝 题目总数', len(pids))
                m2.metric('✅ 已完成', f'{done_count} / {len(pids)}')

                with st.expander('📝 题目列表 + 进度', expanded=True):
                    for idx, pid in enumerate(pids):
                        p = next((pp for pp in all_problems if str(pp.get('id')) == str(pid)), None)
                        title = p.get('title') if p else str(pid)
                        done = False
                        if user:
                            solved_pids2 = set()
                            for s in my_subs:
                                if s.get('status') == 'AC' and s.get('problem_id'):
                                    solved_pids2.add(str(s.get('problem_id')))
                            done = str(pid) in solved_pids2
                        status_icon = '✅' if done else '⬜'
                        col1, col2 = st.columns([8, 1])
                        with col1:
                            st.write(f'{status_icon} **{idx+1}.** `{pid}` - {title}')
                        with col2:
                            st.button('➜ 去做题', key=f'go_judge_{selected_aid}_{pid}',
                                     on_click=goto, kwargs=dict(route_key='judge', id=str(pid)),
                                     use_container_width=True)

                if can_create:
                    edit_btn = st.button('✏️ 编辑作业', key=f'edit_as_{selected_aid}', type='primary')
                    delete_btn = st.button('🗑 删除作业', key=f'del_as_{selected_aid}')

                    if edit_btn:
                        st.session_state[f'editing_aid'] = selected_aid

                    if delete_btn:
                        st.session_state[f'deleting_aid'] = selected_aid

                    if st.session_state.get(f'editing_aid') == selected_aid:
                        with st.expander('✏️ 编辑作业', expanded=True):
                            with st.form(f'as_edit_form_{selected_aid}'):
                                a, b = st.columns(2)
                                cur_pids = [str(p) for p in (selected_assign.get('problem_ids') or [])]
                                cur_pidx = [problem_ids_list.index(p) for p in cur_pids if p in problem_ids_list]
                                with a:
                                    ea_title = st.text_input('作业标题', value=selected_assign.get('title', ''))
                                    cur_cid = str(selected_assign.get('class_id') or '')
                                    ea_cidx = class_ids_list.index(cur_cid) if cur_cid in class_ids_list else 0
                                    ea_class_label = st.selectbox('所属班级', class_labels_list if class_labels_list else ['-'],
                                                                   index=min(ea_cidx, max(0, len(class_labels_list)-1)))
                                    ea_start = st.text_input('开始时间', value=str(selected_assign.get('start_time') or ''))
                                    ea_end = st.text_input('截止时间', value=str(selected_assign.get('end_time') or selected_assign.get('due_date') or ''))
                                with b:
                                    ea_pidx = st.multiselect(
                                        '选择题目',
                                        range(len(problem_labels_list)),
                                        default=cur_pidx,
                                        format_func=lambda i: problem_labels_list[i] if i < len(problem_labels_list) else '',
                                    )
                                    ea_score = st.number_input('每题分值', min_value=1, max_value=100, step=1,
                                                               value=int(selected_assign.get('score_per_problem') or 10))
                                    ea_public = st.checkbox('公开给学生', value=bool(selected_assign.get('is_public', True)))
                                col_save, col_cancel = st.columns(2)
                                with col_save:
                                    save_clicked = st.form_submit_button('💾 保存修改', type='primary', use_container_width=True)
                                with col_cancel:
                                    cancel_clicked = st.form_submit_button('❌ 取消', use_container_width=True)
                            if save_clicked:
                                class_id = None
                                if class_options and ea_class_label in class_labels_list:
                                    idx2 = class_labels_list.index(ea_class_label)
                                    class_id = class_options[idx2][0]
                                new_pids = [problem_ids_list[i] for i in ea_pidx if i < len(problem_ids_list)]
                                payload = {
                                    'title': ea_title,
                                    'class_id': class_id,
                                    'start_time': ea_start or None,
                                    'end_time': ea_end or None,
                                    'problem_ids': new_pids,
                                    'score_per_problem': int(ea_score),
                                    'is_public': bool(ea_public),
                                }
                                c3, d3, err3 = api('PUT', f'/api/assignments/{selected_aid}', payload)
                                if c3 == 200:
                                    toast_safe('作业已更新', 'ok')
                                    st.session_state.pop(f'editing_aid', None)
                                    st.rerun()
                                else:
                                    st.error(f'更新失败：{d3.get("msg") if d3 else err3}')
                            if cancel_clicked:
                                st.session_state.pop(f'editing_aid', None)
                                st.rerun()

                    if st.session_state.get(f'deleting_aid') == selected_aid:
                        with st.expander('⚠️ 确认删除作业', expanded=True):
                            st.warning(f'即将删除作业「{selected_assign.get("title")}」，此操作不可撤销！')
                            confirm_del = st.checkbox('我确认要删除此作业', key=f'confirm_del_as_{selected_aid}')
                            col_del, col_cancel = st.columns(2)
                            with col_del:
                                do_del = st.button('🗑 确认删除', type='primary', use_container_width=True,
                                                   disabled=not confirm_del, key=f'do_del_as_{selected_aid}')
                            with col_cancel:
                                cancel_del = st.button('❌ 取消', key=f'cancel_del_as_{selected_aid}', use_container_width=True)
                            if do_del and confirm_del:
                                c4, d4, err4 = api('DELETE', f'/api/assignments/{selected_aid}')
                                if c4 == 200:
                                    toast_safe('作业已删除', 'ok')
                                    st.session_state.pop(f'deleting_aid', None)
                                    st.rerun()
                                else:
                                    st.error(f'删除失败：{d4.get("msg") if d4 else err4}')
                            if cancel_del:
                                st.session_state.pop(f'deleting_aid', None)
                                st.rerun()

with tab_progress:
    if not user:
        st.caption('请先登录后查看完成情况')
    else:
        my_subs = load_my_submissions(user.get('id'))
        st.caption(f'当前用户：{user.get("username")}，总提交数：{len(my_subs)}')

        user_class_id = str(user.get('class_id') or '')
        my_assigns = [a for a in all_assignments
                      if (str(a.get('class_id')) == user_class_id or not a.get('class_id'))]

        if not my_assigns:
            st.info('（暂未加入任何班级的作业）')
        else:
            progress_rows = []
            for a in my_assigns:
                pids = a.get('problem_ids') or []
                solved_pids = set()
                for s in my_subs:
                    if s.get('status') == 'AC' and s.get('problem_id'):
                        solved_pids.add(str(s.get('problem_id')))
                done = len([pid for pid in pids if str(pid) in solved_pids])
                total = len(pids)
                pct = (done / total * 100) if total > 0 else 0
                progress_rows.append({
                    '作业ID': a.get('id') or '',
                    '作业标题': a.get('title') or '',
                    '进度': f'{done}/{total}',
                    '完成率': f'{pct:.1f}%',
                    '截止时间': str(a.get('end_time') or a.get('due_date') or '-'),
                })
            st.dataframe(pd.DataFrame(progress_rows), use_container_width=True, hide_index=True)

st.caption('© OJ 在线判题平台 · Streamlit 前端 + FastAPI 后端（Python 双栈架构）')
