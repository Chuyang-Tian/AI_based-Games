# -*- coding: utf-8 -*-
"""Streamlit 多页面公共模块。"""

import os
from urllib.parse import quote as url_quote

import requests
import streamlit as st

API_BASE = os.environ.get('OJ_API_BASE', 'http://127.0.0.1:5000')
SESSION_COOKIE_NAME = 'oj_session_id'
SESSION = requests.Session()

ROUTE = {
    'home': 'app_streamlit.py',
    'judge': 'pages/⚖️_判题器.py',
    'problems': 'pages/🗂_题目管理.py',
    'submissions': 'pages/📋_提交日志.py',
    'users': 'pages/👥_用户管理.py',
    'ai': 'pages/🤖_AI命题.py',
    'ai_config': 'pages/⚙️_AI配置.py',
}
ROUTE_ORDER = ['home', 'problems', 'submissions', 'users', 'ai', 'ai_config']
ROUTE_LABELS = {
    'home': '🏠 判题首页',
    'judge': '⚖️ 判题器',
    'problems': '🗂 题目管理',
    'submissions': '📋 提交日志',
    'users': '👥 用户管理',
    'ai': '🤖 AI 命题',
    'ai_config': '⚙️ AI 配置',
}
ROUTE_LABELS_USER = {
    'home': '🏠 判题首页',
    'judge': '⚖️ 判题器',
    'problems': '📚 题库浏览',
    'submissions': '📋 我的提交',
    'ai': '🤖 AI 命题',
}
ROUTE_TO_SLUG = {
    'home': '',
    'judge': '判题器',
    'problems': '题目管理',
    'submissions': '提交日志',
    'users': '用户管理',
    'ai': 'AI命题',
    'ai_config': 'AI配置',
}

MINIMAL_CSS = """
<style>
header[data-testid="stHeader"] {display:none !important;}
section[data-testid="stSidebar"] {display:none !important;}
div[data-testid="stTopBar"] {display:none !important;}
div[data-testid="stAppViewContainer"] {
  display: block !important;
}
div[data-testid="stAppViewContainer"] > div {
  width: 100% !important;
  min-width: 100% !important;
  max-width: 100% !important;
  margin: 0 !important;
}
section[data-testid="stMain"] {
  width: 100% !important;
  max-width: 100% !important;
  margin: 0 auto !important;
  justify-content: center !important;
}
div.block-container,
div[data-testid="stMainBlockContainer"] {
  width: 100% !important;
  max-width: 96rem !important;
  margin-left: auto !important;
  margin-right: auto !important;
  box-sizing: border-box;
  padding-top: 0.75rem;
  padding-bottom: 2rem;
  padding-left: 1.25rem;
  padding-right: 1.25rem;
}
div[data-testid="stAppViewContainer"]::before{
  content:""; display:block; height:6px; width:100%;
  background:linear-gradient(135deg,#c62828 0%,#8e0000 100%);
  border-radius:0 0 8px 8px;
}
</style>
"""


def api(method, path, json_body=None, params=None, timeout=60):
    cookies = {}
    sid = st.session_state.get(SESSION_COOKIE_NAME)
    if sid:
        cookies[SESSION_COOKIE_NAME] = sid
    try:
        response = SESSION.request(
            method,
            f'{API_BASE}{path}',
            json=json_body,
            params=params,
            cookies=cookies,
            timeout=timeout,
        )
    except Exception as exc:
        return 0, None, str(exc)

    try:
        data = response.json()
    except Exception:
        data = None

    if SESSION_COOKIE_NAME in response.cookies:
        st.session_state[SESSION_COOKIE_NAME] = response.cookies[SESSION_COOKIE_NAME]
    return response.status_code, data, None


def current_user():
    return st.session_state.get('oj_me')


def is_admin():
    user = current_user() or {}
    return str(user.get('role', '')).lower() == 'admin'


def is_teacher():
    return is_admin()


def refresh_me():
    code, data, _ = api('GET', '/api/auth/me')
    if code == 200 and isinstance(data, dict) and data.get('data'):
        st.session_state['oj_me'] = data['data']
    elif code == 401:
        st.session_state.pop('oj_me', None)
        st.session_state.pop(SESSION_COOKIE_NAME, None)
    return st.session_state.get('oj_me')


def toast_safe(msg, kind='info'):
    icon = {'ok': '✅', 'warn': '⚠️', 'err': '❌', 'info': 'ℹ️'}.get(kind, 'ℹ️')
    try:
        st.toast(msg, icon=icon)
    except Exception:
        if kind == 'ok':
            st.success(msg)
        elif kind == 'warn':
            st.warning(msg)
        elif kind == 'err':
            st.error(msg)
        else:
            st.info(msg)


def require_login_error():
    st.warning('请先登录后再使用这个页面。')


def require_admin_error():
    st.error('只有管理员可以访问这个页面。')


def clear_problem_cache():
    st.session_state.pop('_all_problems', None)


def goto(route_key, **query_kwargs):
    page_rel = ROUTE.get(route_key)
    if not page_rel:
        return
    params = {}
    for key, value in query_kwargs.items():
        if value is None:
            continue
        params[str(key)] = str(value)
    st.session_state['pending_goto'] = (page_rel, params)
    st.rerun()


@st.dialog('登录 / 注册', width='small')
def login_dialog():
    st.caption('默认管理员：`admin / admintestpassword`')
    mode = st.radio('模式', ['登录', '注册'], horizontal=True, label_visibility='collapsed')
    with st.form('login_register_form'):
        username = st.text_input('用户名')
        password = st.text_input('密码', type='password')
        submitted = st.form_submit_button('提交', type='primary', use_container_width=True)
    if not submitted:
        return
    if not username.strip() or not password:
        st.warning('用户名和密码不能为空')
        return
    if mode == '注册':
        code, data, err = api('POST', '/api/users/', {'username': username.strip(), 'password': password})
        if code != 200:
            st.error(f'注册失败：{data.get("msg") if data else err}')
            return
    code, data, err = api('POST', '/api/auth/login', {'username': username.strip(), 'password': password})
    if code == 200 and isinstance(data, dict):
        refresh_me()
        toast_safe('登录成功', 'ok')
        st.rerun()
    st.error(f'登录失败：{data.get("msg") if data else err}')


def render_topbar(page_tag=''):
    user = current_user()
    with st.container(border=True):
        left, middle, right = st.columns([4, 4, 4])
        with left:
            st.subheader('💻 OJ 调试平台', divider=False)
        with middle:
            if page_tag:
                st.caption(f'📌 {page_tag}')
        with right:
            if user:
                st.write(f'👤 **{user.get("username", "")}**')
                st.caption('管理员' if is_admin() else '普通用户')
                if st.button('退出登录', key='topbar_logout', use_container_width=True):
                    api('POST', '/api/auth/logout')
                    st.session_state.pop('oj_me', None)
                    st.session_state.pop(SESSION_COOKIE_NAME, None)
                    st.rerun()
            else:
                st.caption('当前未登录')
                if st.button('登录 / 注册', key='topbar_login', type='primary', use_container_width=True):
                    login_dialog()


def render_subheader(breadcrumb_parts, active_route='home'):
    label_map = ROUTE_LABELS if is_admin() else ROUTE_LABELS_USER
    with st.container():
        left, right = st.columns([3, 5])
        with left:
            crumbs = []
            for index, (text, _) in enumerate(breadcrumb_parts or []):
                crumbs.append(f'**{text}**' if index == len(breadcrumb_parts) - 1 else f':gray[{text}]')
            st.caption('  ›  '.join(crumbs))
        with right:
            route_keys = [key for key in ROUTE_ORDER if key in label_map]
            columns = st.columns(len(route_keys))
            for index, route_key in enumerate(route_keys):
                slug = ROUTE_TO_SLUG.get(route_key, '')
                target = '/' if not slug else f'/{url_quote(slug)}'
                with columns[index]:
                    st.link_button(
                        label_map[route_key],
                        target,
                        use_container_width=True,
                        type='primary' if route_key == active_route else 'secondary',
                    )


def load_all_problems(force=False):
    if not force and st.session_state.get('_all_problems') is not None:
        return st.session_state['_all_problems']
    code, data, _ = api('GET', '/api/problems/')
    problems = []
    if code == 200 and isinstance(data, dict):
        payload = data.get('data')
        if isinstance(payload, list):
            problems = payload
    if problems and 'description' not in (problems[0] or {}):
        full = []
        for item in problems:
            problem_id = item.get('id')
            detail_code, detail_data, _ = api('GET', f'/api/problems/{problem_id}')
            if detail_code == 200 and isinstance(detail_data, dict) and detail_data.get('data'):
                full.append(detail_data['data'])
            else:
                full.append(item)
        problems = full
    st.session_state['_all_problems'] = problems
    return problems


def load_languages(force=False):
    if not force and st.session_state.get('_all_languages') is not None:
        return st.session_state['_all_languages']
    code, data, _ = api('GET', '/api/languages')
    names = ['python']
    if code == 200 and isinstance(data, dict):
        payload = data.get('data')
        if isinstance(payload, dict) and isinstance(payload.get('name'), list):
            names = [str(item) for item in payload.get('name') if item]
        elif isinstance(payload, list):
            names = [str(item.get('name')) for item in payload if isinstance(item, dict) and item.get('name')]
    names = list(dict.fromkeys(names))
    st.session_state['_all_languages'] = names
    return names


def get_filtered_problems(problems, keyword='', difficulty='', active_tags=None):
    tags_required = set(active_tags or [])
    keyword = (keyword or '').strip().lower()
    result = []
    for problem in problems:
        pid = str(problem.get('id', '')).lower()
        title = str(problem.get('title', '')).lower()
        if keyword and keyword not in pid and keyword not in title:
            continue
        if difficulty and str(problem.get('difficulty', '')) != difficulty:
            continue
        tags = set(problem.get('tags') or [])
        if tags_required and not (tags_required & tags):
            continue
        result.append(problem)
    return result


def ensure_init():
    st.markdown(MINIMAL_CSS, unsafe_allow_html=True)
    pending = st.session_state.pop('pending_goto', None)
    if pending:
        page_path, params = pending
        try:
            for key in list(st.query_params.keys()):
                del st.query_params[key]
        except Exception:
            pass
        for key, value in (params or {}).items():
            st.query_params[key] = value
        try:
            st.switch_page(page_path)
        except Exception:
            pass
    refresh_me()
