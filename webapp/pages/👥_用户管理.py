# -*- coding: utf-8 -*-
"""用户管理页。"""

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
    render_pagination_controls,
    render_subheader,
    render_topbar,
    require_admin_error,
    require_login_error,
    toast_safe,
)

st.set_page_config(page_title='用户管理 · OJ', page_icon='👥', layout='wide', initial_sidebar_state='collapsed')

ensure_init()
render_topbar('用户与权限管理')
render_subheader([('🏠 判题首页', 'home'), ('👥 用户管理', None)], 'users')

user = current_user()
if not user:
    require_login_error()
    st.stop()

if not is_admin():
    require_admin_error()
    st.stop()

page = st.session_state.get('users_page', 1)
page_size = 20
keyword = st.session_state.get('users_keyword', '')

with st.container(border=True):
    st.subheader('筛选与刷新')
    col1, col2, col3 = st.columns([4, 2, 2])
    with col1:
        input_keyword = st.text_input('关键字', value=keyword, placeholder='按用户名搜索')
    with col2:
        if st.button('查询用户', type='primary', use_container_width=True):
            st.session_state['users_keyword'] = input_keyword.strip()
            st.session_state['users_page'] = 1
            st.rerun()
    with col3:
        if st.button('重置筛选', use_container_width=True):
            st.session_state['users_keyword'] = ''
            st.session_state['users_page'] = 1
            st.rerun()

params = {'page': page, 'page_size': page_size}
if st.session_state.get('users_keyword'):
    params['keyword'] = st.session_state['users_keyword']
code, data, err = api('GET', '/api/users', params=params)
payload = data.get('data') if isinstance(data, dict) else {}
users = payload.get('users') if isinstance(payload, dict) else []
total = int(payload.get('total', 0) or 0) if isinstance(payload, dict) else 0
total_pages = max(1, math.ceil(total / page_size)) if total else 1
page = min(max(1, int(page or 1)), total_pages)
if int(st.session_state.get('users_page', 1) or 1) != page:
    st.session_state['users_page'] = page
    st.rerun()

with st.container(border=True):
    st.subheader('创建管理员账号')
    with st.form('create_admin_form'):
        c1, c2 = st.columns(2)
        with c1:
            admin_username = st.text_input('管理员用户名')
        with c2:
            admin_password = st.text_input('管理员密码', type='password')
        submitted = st.form_submit_button('创建管理员', type='primary', use_container_width=True)
    if submitted:
        create_code, create_data, create_err = api(
            'POST',
            '/api/users/admin',
            {'username': admin_username.strip(), 'password': admin_password},
        )
        if create_code == 200:
            toast_safe('管理员创建成功', 'ok')
            st.rerun()
        st.error(f'创建失败：{create_data.get("msg") if create_data else create_err}')

rows = []
for item in users or []:
    rows.append({
        '用户 ID': item.get('user_id', ''),
        '用户名': item.get('username', ''),
        '角色': item.get('role', ''),
        '加入时间': item.get('join_time', ''),
        '提交数': item.get('submit_count', 0),
        '通过题数': item.get('resolve_count', 0),
    })

with st.container(border=True):
    st.subheader('用户列表')
    stats = st.columns(4)
    stats[0].metric('当前页用户数', len(rows))
    stats[1].metric('查询总数', total)
    stats[2].metric('管理员数', sum(1 for row in rows if row['角色'] == 'admin'))
    stats[3].metric('封禁数', sum(1 for row in rows if row['角色'] == 'banned'))
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info('当前筛选下没有用户记录。')

if rows:
    with st.container(border=True):
        st.subheader('角色调整')
        choice_map = {f"{row['用户 ID']} · {row['用户名']}": row for row in rows}
        selection = st.selectbox('选择用户', list(choice_map.keys()))
        selected = choice_map[selection]
        role_options = ['user', 'admin', 'banned']
        current_role = selected['角色'] if selected['角色'] in role_options else 'user'
        new_role = st.selectbox('新角色', role_options, index=role_options.index(current_role))
        if st.button('更新角色', type='primary', use_container_width=True):
            update_code, update_data, update_err = api(
                'PUT',
                f"/api/users/{selected['用户 ID']}/role",
                {'role': new_role},
            )
            if update_code == 200:
                toast_safe('角色更新成功', 'ok')
                st.rerun()
            st.error(f'更新失败：{update_data.get("msg") if update_data else update_err}')

render_pagination_controls(
    'users_page',
    page,
    total_pages,
    page_size,
    total_items=total,
)
