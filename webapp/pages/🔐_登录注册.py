# -*- coding: utf-8 -*-
"""
登录 / 注册页——Step4 用户管理的核心前端入口。
= 功能分区 =
  - 单选：登录 / 注册 两种模式；
  - 登录：输入用户名+密码 → POST /api/auth/login → 拿到 oj_session_id cookie（common.SESSION 自动保存）
          → 刷新 st.session_state['oj_me'] → 跳首页；
  - 注册：用户名+密码+确认密码 → POST /api/auth/register → 创建 users 表一条 user 角色账号
          → 自动登录进入系统；
  - 已登录态：显示"你已经登录"，提供返回首页 / 退出登录两个动作。
= Step4 对应点 =
  5 分用户管理里"注册+登录+登出+权限分级（admin/user/banned）"的所有 UI 交互都在这里。
= 与其他页面的连接 =
  - 顶栏任何"请先登录"按钮 → 跳 /登录注册；
  - 登录成功后 common.refresh_me() 把当前用户信息写进 st.session_state，
    后续个人信息页、判题页、提交页都靠这个对象判断登录态和权限。
"""

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
render_topbar('账号入口', on_auth_page=True)
render_subheader([('🏠 判题首页', 'home'), ('🔐 登录 / 注册', None)], 'home')

user = current_user()

with st.container(border=True):
    if user:
        st.subheader('你已经登录')
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
        st.subheader('登录 / 注册')
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
