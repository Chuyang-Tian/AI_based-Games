# -*- coding: utf-8 -*-
"""
个人信息页——Step6 前端交互（5分）里「用户页面组」的必选页面之一。
= 页面展示 =
  1. 顶部：面包屑「🏠 判题首页 › 👤 个人信息」；
  2. 6 个 metric 卡片（st.metric）：
       用户 ID / 用户名 / 角色 / 注册时间 / 提交次数 / 通过题目数
     全部走 `_clean(x, default='-')` 清洗——去掉 \r\n 换行、strip，None 转 '-'，
     修复 v1.4.0 之前「用户名和 ID 显示 '-' / 空行 / 'None'」的 bug；
  3. 字段明细表格（st.dataframe，6 行字段+值），metric 与表格同步；
  4. 底部两按钮：
       📚 开始做题（进入题库） → common.page_url('problems') 跳 /题目管理
          （v1.4.1 修复：之前 page_url('judge') 会跳到 ⚖️判题器，但判题器需要 ?id=xxx 才有效，死链；
           「开始做题」的正确语义应该是"去题库选一道"，所以改成 problems 页）；
       📋 查看我的提交 → common.page_url('submissions') 跳 /提交日志。
= 统计同步机制（v1.4.1 新增核心）=
  本页调用 `_load_profile(uid)` → GET /api/users/{uid}：
    后端 app_fastapi.api_user_info() 在返回前会调 userdb.recompute_user_stats(uid)
    实查 submissions 表 COUNT 与 COUNT(DISTINCT problem_id WHERE AC & pass=total>0)，
    再 UPDATE users.submit_count / resolve_count，保证：
      ① 用户看到的数字永远是最新的，不会因为"历史数据/重判"而陈旧；
      ② DB 里的 users 表列也同步被修正，避免缓存/快照导致的不一致。
= Step6 对应点 =
  用户页面组（4 页必选：登录注册 / 个人信息 / 我的提交 / 用户管理）里，本页就是"个人信息"那一项；
  题目组 / 评测提交组则由 🗂题目管理、📄题目详情、⚖️判题器、📋提交日志、🧾提交详情 5 页共同完成，
  符合 Step6 "三类页面每组至少 5/4/5 个页面" 的规范。
= 调试点 =
  若 metric 还是 '-'，优先检查：
    (1) FastAPI :5000 是否 LISTENING（登录 123321 失败 Max retries 一般就是这个原因）；
    (2) _load_profile() 返回的 payload 是否为 {code:200, data:{...}}——本模块会先解包 payload['data']，
        以前版本错把外层 payload 直接当 data 用，就是全 '-' 的根因。
"""

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
    """
    拉取当前用户信息。
    common.api 返回 (http_code, payload_dict_or_None, err) 三元组；
    payload_dict 是 FastAPI _api_response() 的包装：{code:int, msg:str, data:dict_or_list}
    所以业务数据要从 payload['data'] 取，之前版本的 bug 就是这里错把外层 payload 当 data。
    """
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
