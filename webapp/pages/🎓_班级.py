# -*- coding: utf-8 -*-
"""
🎓 班级管理（route_key=classes，teacher/admin 可见）
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
st.set_page_config(page_title='班级管理 - OJ', page_icon='🎓', layout='wide',
                   initial_sidebar_state='collapsed')

from common import (
    ensure_init, render_topbar, render_subheader,
    current_user, require_login_error, is_admin, is_teacher,
    api, toast_safe, load_all_problems,
)

ensure_init()
render_topbar('班级管理')
render_subheader([
    ('🏠 判题首页', 'home'),
    ('🎓 班级', None),
], 'classes')
user = current_user()

if not user:
    require_login_error()
    st.stop()

if not (is_admin() or is_teacher()):
    st.error('⛔ 需要教师或管理员权限才能访问此页面。')
    st.stop()

import pandas as pd

def load_classes():
    c, d, _ = api('GET', '/api/classes/')
    if c == 200 and isinstance(d, dict):
        data = d.get('data')
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get('list') or data.get('items') or []
    return []

def load_teachers():
    c, d, _ = api('GET', '/api/users/')
    users = []
    if c == 200 and isinstance(d, dict):
        data = d.get('data')
        if isinstance(data, list):
            users = data
        elif isinstance(data, dict):
            users = data.get('list') or data.get('users') or data.get('items') or []
    return [u for u in users if str(u.get('role', '')) in ('teacher', 'admin')]

def load_students():
    c, d, _ = api('GET', '/api/users/')
    users = []
    if c == 200 and isinstance(d, dict):
        data = d.get('data')
        if isinstance(data, list):
            users = data
        elif isinstance(data, dict):
            users = data.get('list') or data.get('users') or data.get('items') or []
    return [u for u in users if str(u.get('role', '')) == 'student']

def load_class_students(cid):
    c, d, _ = api('GET', f'/api/classes/{cid}/students')
    if c == 200 and isinstance(d, dict):
        data = d.get('data')
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get('list') or data.get('students') or data.get('members') or []
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

all_classes = load_classes()
all_teachers = load_teachers()
all_students = load_students()
all_assignments = load_assignments()
all_problems = load_all_problems()

with st.container(border=True):
    st.subheader('➕ 新建班级')
    with st.form('class_add_form'):
        a, b = st.columns(2)
        with a:
            nc_name = st.text_input('班级名称 *')
            nc_desc = st.text_area('班级描述', height=80)
        with b:
            teacher_options = [(t.get('id'), f"{t.get('username')} ({t.get('real_name') or t.get('username')})") for t in all_teachers]
            teacher_ids = [str(to[0]) for to in teacher_options]
            teacher_labels = [to[1] for to in teacher_options]
            nc_teacher_idx = 0
            nc_teacher_label = st.selectbox('班主任 / 授课老师', teacher_labels if teacher_labels else ['-'], index=nc_teacher_idx)
        if st.form_submit_button('✅ 创建班级', type='primary', use_container_width=True):
            if not nc_name:
                st.error('班级名称为必填项')
            else:
                teacher_id = None
                if teacher_options and nc_teacher_label in teacher_labels:
                    idx = teacher_labels.index(nc_teacher_label)
                    teacher_id = teacher_options[idx][0]
                payload = {
                    'name': nc_name,
                    'description': nc_desc or None,
                    'teacher_id': teacher_id,
                }
                c2, d2, err = api('POST', '/api/classes/', payload)
                if c2 == 200:
                    toast_safe('班级创建成功', 'ok')
                    st.rerun()
                else:
                    st.error(f'创建失败：{d2.get("msg") if d2 else err}')

total_classes = len(all_classes)
total_students = len(all_students)
total_teachers = len(all_teachers)

m1, m2, m3 = st.columns(3)
m1.metric('🎓 总班级数', total_classes)
m2.metric('👥 学生总数', total_students)
m3.metric('👨‍🏫 教师数', total_teachers)

with st.container(border=True):
    st.subheader('📋 班级列表')
    rows = []
    for cls in all_classes:
        rows.append({
            'ID': cls.get('id') or '',
            '班级名称': cls.get('name') or '',
            '描述': (cls.get('description') or '')[:50],
            '班主任': cls.get('teacher_name') or cls.get('teacher_username') or '-',
            '学生数': cls.get('student_count') or cls.get('member_count') or 0,
            '创建时间': str(cls.get('created_at') or ''),
        })
    if not rows:
        st.info('（暂无班级）')
    else:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

class_ids = [str(r['ID']) for r in rows if r['ID']]
if class_ids:
    with st.container(border=True):
        st.subheader('🛠 班级操作')
        col_sel, col_btn1, col_btn2 = st.columns([2, 1, 1])
        with col_sel:
            selected_cid = st.selectbox('选择班级 ID', class_ids)
        selected_cls = next((c for c in all_classes if str(c.get('id')) == selected_cid), None)

        if selected_cls:
            with col_btn1:
                edit_btn = st.button('✏️ 编辑班级', use_container_width=True, type='primary')
            with col_btn2:
                delete_btn = st.button('🗑 删除班级', use_container_width=True)

            if edit_btn:
                st.session_state['editing_cid'] = selected_cid

            if delete_btn:
                st.session_state['deleting_cid'] = selected_cid

            if st.session_state.get('editing_cid') == selected_cid:
                with st.expander('✏️ 编辑班级详情', expanded=True):
                    with st.form('class_edit_form'):
                        a, b = st.columns(2)
                        with a:
                            ec_name = st.text_input('班级名称', value=selected_cls.get('name', ''))
                            ec_desc = st.text_area('班级描述', value=selected_cls.get('description', '') or '', height=80)
                        with b:
                            cur_tid = str(selected_cls.get('teacher_id') or '')
                            ec_teacher_idx = teacher_ids.index(cur_tid) if cur_tid in teacher_ids else 0
                            ec_teacher_label = st.selectbox('班主任 / 授课老师', teacher_labels if teacher_labels else ['-'],
                                                             index=min(ec_teacher_idx, max(0, len(teacher_labels)-1)))
                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            save_clicked = st.form_submit_button('💾 保存修改', type='primary', use_container_width=True)
                        with col_cancel:
                            cancel_clicked = st.form_submit_button('❌ 取消', use_container_width=True)
                    if save_clicked:
                        teacher_id = None
                        if teacher_options and ec_teacher_label in teacher_labels:
                            idx = teacher_labels.index(ec_teacher_label)
                            teacher_id = teacher_options[idx][0]
                        payload = {
                            'name': ec_name,
                            'description': ec_desc or None,
                            'teacher_id': teacher_id,
                        }
                        c3, d3, err3 = api('PUT', f'/api/classes/{selected_cid}', payload)
                        if c3 == 200:
                            toast_safe('班级信息已更新', 'ok')
                            st.session_state.pop('editing_cid', None)
                            st.rerun()
                        else:
                            st.error(f'更新失败：{d3.get("msg") if d3 else err3}')
                    if cancel_clicked:
                        st.session_state.pop('editing_cid', None)
                        st.rerun()

            if st.session_state.get('deleting_cid') == selected_cid:
                with st.expander('⚠️ 确认删除班级', expanded=True):
                    st.warning(f'即将删除班级「{selected_cls.get("name")}」，此操作不可撤销！')
                    confirm_del = st.checkbox('我确认要删除此班级及其关联数据')
                    col_del, col_cancel = st.columns(2)
                    with col_del:
                        do_del = st.button('🗑 确认删除', type='primary', use_container_width=True, disabled=not confirm_del)
                    with col_cancel:
                        cancel_del = st.button('❌ 取消', use_container_width=True)
                    if do_del and confirm_del:
                        c4, d4, err4 = api('DELETE', f'/api/classes/{selected_cid}')
                        if c4 == 200:
                            toast_safe('班级已删除', 'ok')
                            st.session_state.pop('deleting_cid', None)
                            st.rerun()
                        else:
                            st.error(f'删除失败：{d4.get("msg") if d4 else err4}')
                    if cancel_del:
                        st.session_state.pop('deleting_cid', None)
                        st.rerun()

            if selected_cls:
                cid = selected_cls.get('id')
                with st.container(border=True):
                    st.subheader(f'📂 班级详情：{selected_cls.get("name")}')
                    tab_members, tab_problems, tab_assigns = st.tabs(['👥 班级成员', '📚 题目列表', '📝 作业列表'])

                    with tab_members:
                        current_class_students = load_class_students(cid)
                        current_student_ids = set(str(s.get('id')) for s in current_class_students)
                        student_options = [(str(s.get('id')), f"{s.get('username')} ({s.get('real_name') or s.get('username')})") for s in all_students]
                        student_ids_list = [so[0] for so in student_options]
                        student_labels_list = [so[1] for so in student_options]
                        default_selected = [sid for sid in current_student_ids if sid in student_ids_list]
                        default_indices = [student_ids_list.index(sid) for sid in default_selected if sid in student_ids_list]

                        st.caption(f'当前班级学生数：{len(current_class_students)}')
                        selected_student_indices = st.multiselect(
                            '选择班级成员（勾选 / 取消勾选后点保存）',
                            range(len(student_labels_list)),
                            default=default_indices,
                            format_func=lambda i: student_labels_list[i] if i < len(student_labels_list) else '',
                        )
                        if st.button('💾 保存成员变更', key='save_members', type='primary'):
                            new_student_ids = [student_ids_list[i] for i in selected_student_indices if i < len(student_ids_list)]
                            c5, d5, err5 = api('PATCH', f'/api/classes/{cid}/students', {'student_ids': new_student_ids})
                            if c5 == 200:
                                toast_safe('班级成员已更新', 'ok')
                                st.rerun()
                            else:
                                st.error(f'保存失败：{d5.get("msg") if d5 else err5}')

                        if current_class_students:
                            mrows = []
                            for s in current_class_students:
                                mrows.append({
                                    'ID': s.get('id') or '',
                                    '用户名': s.get('username') or '',
                                    '真实姓名': s.get('real_name') or '-',
                                    '邮箱': s.get('email') or '-',
                                })
                            st.dataframe(pd.DataFrame(mrows), use_container_width=True, hide_index=True)
                        else:
                            st.caption('（暂无成员）')

                    with tab_problems:
                        class_problems = [p for p in all_problems if str(p.get('class_id')) == str(cid)]
                        st.caption(f'该班级关联题目数：{len(class_problems)}')
                        if class_problems:
                            prows = []
                            for p in class_problems:
                                prows.append({
                                    'ID': p.get('id') or '',
                                    '标题': p.get('title') or '',
                                    '难度': p.get('difficulty') or '-',
                                    '标签': ', '.join(p.get('tags') or []) or '-',
                                })
                            st.dataframe(pd.DataFrame(prows), use_container_width=True, hide_index=True)
                        else:
                            st.caption('（暂无该班级专属题目）')

                    with tab_assigns:
                        class_assigns = [a for a in all_assignments if str(a.get('class_id')) == str(cid)]
                        st.caption(f'该班级作业数：{len(class_assigns)}')
                        if class_assigns:
                            arows = []
                            for a in class_assigns:
                                arows.append({
                                    'ID': a.get('id') or '',
                                    '标题': a.get('title') or '',
                                    '题目数': len(a.get('problem_ids') or []) or 0,
                                    '开始时间': str(a.get('start_time') or '-'),
                                    '截止时间': str(a.get('end_time') or a.get('due_date') or '-'),
                                })
                            st.dataframe(pd.DataFrame(arows), use_container_width=True, hide_index=True)
                        else:
                            st.caption('（暂无作业）')

st.caption('© OJ 在线判题平台 · Streamlit 前端 + FastAPI 后端（Python 双栈架构）')
