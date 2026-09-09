# -*- coding: utf-8 -*-
"""
👥 用户管理（route_key=users，管理员/老师可见）
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
st.set_page_config(page_title='用户管理 - OJ', page_icon='👥', layout='wide',
                   initial_sidebar_state='collapsed')

from common import (
    ensure_init, render_topbar, render_subheader,
    current_user, require_login_error, require_admin_error, is_admin, is_teacher,
    api, toast_safe,
)

ensure_init()
render_topbar('用户管理')
render_subheader([
    ('🏠 判题首页', 'home'),
    ('👥 用户管理', None),
], 'users')
user = current_user()

if not user:
    require_login_error()
    st.stop()

if not (is_admin() or is_teacher()):
    require_admin_error()
    st.stop()

import pandas as pd

ROLES = ['student', 'teacher', 'admin']
STATUS_OPTIONS = ['all', 'active', 'disabled']

def load_users():
    c, d, _ = api('GET', '/api/users/')
    if c == 200 and isinstance(d, dict):
        data = d.get('data')
        if isinstance(data, dict):
            return data.get('list') or data.get('users') or data.get('items') or []
        if isinstance(data, list):
            return data
    return []

all_users = load_users()

with st.container(border=True):
    st.subheader('🔍 筛选用户')
    with st.form('user_filter_form'):
        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
        with col1:
            keyword = st.text_input('搜索', placeholder='用户名 / 邮箱 / 手机号')
        with col2:
            role_filter = st.multiselect('角色', ROLES, default=[])
        with col3:
            status_filter = st.radio('状态', STATUS_OPTIONS, horizontal=True)
        with col4:
            st.write('')
            st.write('')
            submitted = st.form_submit_button('🔍 筛选', type='primary', use_container_width=True)

if is_admin():
    with st.container(border=True):
        st.subheader('➕ 新建用户')
        with st.form('user_add_form'):
            a, b, c = st.columns(3)
            with a:
                nu_username = st.text_input('用户名 *')
                nu_email = st.text_input('邮箱')
            with b:
                nu_password = st.text_input('密码 *', type='password')
                nu_phone = st.text_input('手机号')
            with c:
                nu_role = st.selectbox('角色', ROLES, index=0)
                nu_status = st.selectbox('状态', ['active', 'disabled'], index=0)
            if st.form_submit_button('✅ 创建用户', type='primary', use_container_width=True):
                if not nu_username or not nu_password:
                    st.error('用户名和密码为必填项')
                else:
                    payload = {
                        'username': nu_username,
                        'password': nu_password,
                        'email': nu_email or None,
                        'phone': nu_phone or None,
                        'role': nu_role,
                        'status': nu_status,
                    }
                    c2, d2, err = api('POST', '/api/users/', payload)
                    if c2 == 200:
                        toast_safe('用户创建成功', 'ok')
                        st.rerun()
                    else:
                        st.error(f'创建失败：{d2.get("msg") if d2 else err}')

filtered = all_users
if keyword:
    kw = keyword.lower()
    filtered = [u for u in filtered if
                kw in str(u.get('username', '')).lower() or
                kw in str(u.get('email', '')).lower() or
                kw in str(u.get('phone', '')).lower()]
if role_filter:
    filtered = [u for u in filtered if u.get('role') in role_filter]
if status_filter != 'all':
    filtered = [u for u in filtered if str(u.get('status', 'active')) == status_filter]

total_users = len(all_users)
student_count = len([u for u in all_users if str(u.get('role', '')) == 'student'])
teacher_count = len([u for u in all_users if str(u.get('role', '')) == 'teacher'])

m1, m2, m3 = st.columns(3)
m1.metric('👥 总用户数', total_users)
m2.metric('🎓 学生数', student_count)
m3.metric('👨‍🏫 教师数', teacher_count)

with st.container(border=True):
    st.subheader('📋 用户列表')
    rows = []
    for u in filtered:
        rows.append({
            'ID': u.get('id') or '',
            '用户名': u.get('username') or '',
            '邮箱': u.get('email') or '-',
            '手机号': u.get('phone') or '-',
            '角色': u.get('role') or '',
            '状态': u.get('status') or 'active',
            '注册时间': str(u.get('created_at') or u.get('register_time') or ''),
        })
    if not rows:
        st.info('（暂无符合条件的用户）')
    else:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

user_ids = [str(r['ID']) for r in rows if r['ID']]
if user_ids:
    with st.container(border=True):
        st.subheader('🛠 用户操作')
        col_sel, col_btn1, col_btn2 = st.columns([2, 1, 1])
        with col_sel:
            selected_uid = st.selectbox('选择用户 ID', user_ids)
        selected_user = next((u for u in filtered if str(u.get('id')) == selected_uid), None)

        if selected_user:
            with col_btn1:
                edit_btn = st.button('✏️ 编辑用户', use_container_width=True, type='primary')
            with col_btn2:
                cur_status = selected_user.get('status', 'active')
                toggle_label = '🚫 禁用' if cur_status == 'active' else '✅ 启用'
                toggle_btn = st.button(toggle_label, use_container_width=True)

            if edit_btn:
                st.session_state['editing_uid'] = selected_uid

            if toggle_btn:
                new_status = 'disabled' if cur_status == 'active' else 'active'
                c3, d3, err3 = api('PATCH', f'/api/users/{selected_uid}', {'status': new_status})
                if c3 == 200:
                    toast_safe(f'用户状态已更新为 {new_status}', 'ok')
                    st.rerun()
                else:
                    st.error(f'操作失败：{d3.get("msg") if d3 else err3}')

            if st.session_state.get('editing_uid') == selected_uid:
                with st.expander('✏️ 编辑用户详情', expanded=True):
                    with st.form('user_edit_form'):
                        a, b, c = st.columns(3)
                        with a:
                            eu_username = st.text_input('用户名', value=selected_user.get('username', ''))
                            eu_email = st.text_input('邮箱', value=selected_user.get('email', '') or '')
                        with b:
                            eu_password = st.text_input('新密码（留空不改）', type='password')
                            eu_phone = st.text_input('手机号', value=selected_user.get('phone', '') or '')
                        with c:
                            cur_role = selected_user.get('role', 'student')
                            eu_role_idx = ROLES.index(cur_role) if cur_role in ROLES else 0
                            eu_role = st.selectbox('角色', ROLES, index=eu_role_idx)
                            cur_st = selected_user.get('status', 'active')
                            eu_st_idx = 0 if cur_st == 'active' else 1
                            eu_status = st.selectbox('状态', ['active', 'disabled'], index=eu_st_idx)
                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            save_clicked = st.form_submit_button('💾 保存修改', type='primary', use_container_width=True)
                        with col_cancel:
                            cancel_clicked = st.form_submit_button('❌ 取消', use_container_width=True)
                    if save_clicked:
                        payload = {
                            'username': eu_username,
                            'email': eu_email or None,
                            'phone': eu_phone or None,
                            'role': eu_role,
                            'status': eu_status,
                        }
                        if eu_password:
                            payload['password'] = eu_password
                        c4, d4, err4 = api('PUT', f'/api/users/{selected_uid}', payload)
                        if c4 == 200:
                            toast_safe('用户信息已更新', 'ok')
                            st.session_state.pop('editing_uid', None)
                            st.rerun()
                        else:
                            st.error(f'更新失败：{d4.get("msg") if d4 else err4}')
                    if cancel_clicked:
                        st.session_state.pop('editing_uid', None)
                        st.rerun()

st.caption('© OJ 在线判题平台 · Streamlit 前端 + FastAPI 后端（Python 双栈架构）')
