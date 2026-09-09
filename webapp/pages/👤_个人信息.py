# -*- coding: utf-8 -*-
"""用户信息展示页（Step6 用户页面组必选项）。"""

import os
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import (
    api,
    current_user,
    ensure_init,
    is_admin,
    page_url,
    render_page_link,
    render_subheader,
    render_topbar,
    require_login_error,
    tr,
)

st.set_page_config(page_title='个人信息 · OJ', page_icon='👤', layout='wide', initial_sidebar_state='collapsed')

ensure_init()
render_topbar('个人信息')
render_subheader([('🏠 判题首页', 'home'), ('👤 个人信息', None)], 'profile')

user = current_user()
if not user:
    require_login_error()
    st.stop()


def _load_profile(uid):
    r = api('GET', f'/api/users/{uid}')
    code, payload, err = r if isinstance(r, (list, tuple)) and len(r) >= 3 else (r.get('code') if isinstance(r, dict) else 0, r.get('data') if isinstance(r, dict) else None, str(r))
    ok = code == 200 and isinstance(payload, dict) and payload.get('data')
    return ok, (payload['data'] if ok else (payload or r))


ok, resp = _load_profile(user.get('user_id'))
if not ok:
    st.error(tr('profile_load_error', '加载个人信息失败: {msg}').format(msg=str(resp)))
    st.stop()

data = resp if isinstance(resp, dict) else resp['data']


def _clean(x, default=''):
    if x is None:
        return default
    s = str(x)
    s = s.replace('\r', '').replace('\n', ' ').strip()
    if not s:
        return default
    return s


role_map = {
    'admin': '🛡 ' + tr('role_admin', '管理员'),
    'user': '👤 ' + tr('role_user', '普通用户'),
    'banned': '🚫 ' + tr('role_banned', '已封禁'),
}
role_label = role_map.get(data.get('role', ''), _clean(data.get('role', '')))

st.markdown('### 👤 ' + tr('profile_title', '个人信息'))
cols = st.columns([1.1, 1.5, 1.1])
with cols[0]:
    st.metric(tr('pf_user_id', '用户 ID'), _clean(data.get('user_id', ''), '-'))
with cols[1]:
    st.metric(tr('pf_username', '用户名'), _clean(data.get('username', ''), '-'))
with cols[2]:
    st.metric(tr('pf_role', '角色'), role_label)

cols2 = st.columns([1.5, 1.1, 1.1])
with cols2[0]:
    st.metric(tr('pf_join', '注册时间'), _clean(data.get('join_time', ''), '-'))
with cols2[1]:
    st.metric(tr('pf_submit', '提交次数'), _clean(data.get('submit_count', 0), '0'))
with cols2[2]:
    st.metric(tr('pf_resolve', '通过题目数'), _clean(data.get('resolve_count', 0), '0'))

st.markdown('---')
st.subheader(tr('pf_detail_table', '字段明细'))
rows = [
    (tr('pf_user_id', '用户 ID'), _clean(data.get('user_id', ''), '-')),
    (tr('pf_username', '用户名'), _clean(data.get('username', ''), '-')),
    (tr('pf_role', '角色'), role_label),
    (tr('pf_join', '注册时间'), _clean(data.get('join_time', ''), '-')),
    (tr('pf_submit', '提交次数'), _clean(data.get('submit_count', 0), '0')),
    (tr('pf_resolve', '通过题目数'), _clean(data.get('resolve_count', 0), '0')),
]
st.dataframe(pd.DataFrame(rows, columns=[tr('pf_field', '字段'), tr('pf_value', '值')]), use_container_width=True, hide_index=True)

st.markdown('---')
nav_cols = st.columns(3)
with nav_cols[0]:
    render_page_link('📚 ' + tr('go_judge', '开始做题（进入题库）'), page_url('problems'), primary=True)
with nav_cols[1]:
    render_page_link('📋 ' + tr('go_submissions', '查看我的提交'), page_url('submissions'))
with nav_cols[2]:
    if is_admin():
        render_page_link('👥 ' + tr('go_users', '用户管理'), page_url('users'))
