# -*- coding: utf-8 -*-
"""登录 / 注册独立页面。"""

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import (
    api,
    current_user,
    ensure_init,
    page_url,
    refresh_me,
    render_page_link,
    render_subheader,
    render_topbar,
    toast_safe,
)


st.set_page_config(page_title='登录 / 注册 · OJ', page_icon='🔐', layout='wide', initial_sidebar_state='collapsed')

ensure_init()
render_topbar('账号入口')
render_subheader([('🏠 判题首页', 'home'), ('🔐 登录 / 注册', None)], 'home')

user = current_user()

with st.container(border=True):
    if user:
        st.subheader('你已经登录', divider=False)
        st.caption(f"当前账号：{user.get('username', '')}（{user.get('role', '') or 'user'}）")
        left, right = st.columns(2)
        with left:
            render_page_link('返回首页', page_url('home'), primary=True)
        with right:
            if st.button('退出登录', use_container_width=True):
                api('POST', '/api/auth/logout')
                st.session_state.pop('oj_me', None)
                st.session_state.pop('oj_session_id', None)
                toast_safe('已退出登录', 'ok')
                st.rerun()
    else:
        st.subheader('登录 / 注册', divider=False)
        st.caption('默认管理员：`admin / admintestpassword`')
        mode = st.radio('模式', ['登录', '注册'], horizontal=True, label_visibility='collapsed')
        with st.form('auth_page_form'):
            username = st.text_input('用户名')
            password = st.text_input('密码', type='password')
            confirm_password = ''
            if mode == '注册':
                confirm_password = st.text_input('确认密码', type='password')
            submitted = st.form_submit_button('提交', type='primary', use_container_width=True)

        if submitted:
            if not username.strip() or not password:
                st.warning('用户名和密码不能为空')
            elif mode == '注册' and password != confirm_password:
                st.warning('两次输入的密码不一致')
            else:
                if mode == '注册':
                    reg_code, reg_data, reg_err = api('POST', '/api/users/', {'username': username.strip(), 'password': password})
                    if reg_code != 200:
                        st.error(f'注册失败：{reg_data.get("msg") if reg_data else reg_err}')
                        st.stop()
                code, data, err = api('POST', '/api/auth/login', {'username': username.strip(), 'password': password})
                if code == 200 and isinstance(data, dict):
                    refresh_me()
                    toast_safe('登录成功', 'ok')
                    st.rerun()
                st.error(f'登录失败：{data.get("msg") if data else err}')
