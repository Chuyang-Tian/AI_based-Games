# -*- coding: utf-8 -*-
"""Streamlit 多页面公共模块。"""

import html
import os
import re
from urllib.parse import quote as url_quote, urlencode


import requests
import streamlit as st

API_BASE = os.environ.get('OJ_API_BASE', 'http://127.0.0.1:5000')
SESSION_COOKIE_NAME = 'oj_session_id'
SESSION = requests.Session()

ROUTE = {
    'home': 'app_streamlit.py',
    'auth': 'pages/🔐_登录注册.py',
    'judge': 'pages/⚖️_判题器.py',
    'classes': 'pages/🎓_班级.py',
    'assignments': 'pages/📝_作业.py',
    'exams': 'pages/📝_考试.py',
    'problems': 'pages/🗂_题目管理.py',
    'problem_detail': 'pages/📄_题目详情.py',
    'submissions': 'pages/📋_提交日志.py',
    'submission_detail': 'pages/🧾_提交详情.py',
    'users': 'pages/👥_用户管理.py',
    'ai': 'pages/🤖_AI命题.py',
    'ai_config': 'pages/⚙️_AI配置.py',
}
ROUTE_ORDER = ['home', 'classes', 'assignments', 'exams', 'problems', 'submissions', 'users', 'ai', 'ai_config']
ROUTE_LABELS_ZH = {
    'home': '🏠 判题首页',
    'auth': '🔐 登录 / 注册',
    'classes': '🎓 班级',
    'assignments': '📝 作业',
    'exams': '📝 考试',
    'judge': '⚖️ 判题器',
    'problems': '🗂 题目管理',
    'submissions': '📋 提交日志',
    'users': '👥 用户管理',
    'ai': '🤖 AI 命题',
    'ai_config': '⚙️ AI 配置',
}
ROUTE_LABELS_USER_ZH = {
    'home': '🏠 判题首页',
    'auth': '🔐 登录 / 注册',
    'classes': '🎓 我的班级',
    'assignments': '📝 我的作业',
    'exams': '📝 我的考试',
    'judge': '⚖️ 判题器',
    'problems': '📚 题库浏览',
    'submissions': '📋 我的提交',
    'ai': '🤖 AI 命题',
}
ROUTE_LABELS_EN = {
    'home': '🏠 Home',
    'auth': '🔐 Login',
    'classes': '🎓 Classes',
    'assignments': '📝 Assignments',
    'exams': '📝 Exams',
    'judge': '⚖️ Judge',
    'problems': '🗂 Problem Admin',
    'submissions': '📋 Submissions',
    'users': '👥 Users',
    'ai': '🤖 AI Problem Gen',
    'ai_config': '⚙️ AI Config',
}
ROUTE_LABELS_USER_EN = {
    'home': '🏠 Home',
    'auth': '🔐 Login',
    'classes': '🎓 My Classes',
    'assignments': '📝 My Assignments',
    'exams': '📝 My Exams',
    'judge': '⚖️ Judge',
    'problems': '📚 Problemset',
    'submissions': '📋 My Submissions',
    'ai': '🤖 AI Problem Gen',
}
ROUTE_TO_SLUG = {
    'home': '',
    'auth': '登录注册',
    'classes': '班级',
    'assignments': '作业',
    'exams': '考试',
    'judge': '判题器',
    'problems': '题目管理',
    'problem_detail': '题目详情',
    'submissions': '提交日志',
    'submission_detail': '提交详情',
    'users': '用户管理',
    'ai': 'AI命题',
    'ai_config': 'AI配置',
}

THEME_OPTIONS = {
    'red': {
        'label': '红',
        'accent_1': '#c62828',
        'accent_2': '#8e0000',
        'accent_soft': '#fff5f5',
        'accent_border': '#fecaca',
        'accent_text': '#b91c1c',
        'surface_soft': '#faf7f7',
        'surface_muted': '#f5f1f1',
        'surface_border': '#eadede',
        'surface_hover': '#f2e8e8',
        'text_soft': '#6b7280',
        'text_main': '#111827',
    },
    'pink': {
        'label': '粉',
        'accent_1': '#d81b60',
        'accent_2': '#ad1457',
        'accent_soft': '#fdf2f8',
        'accent_border': '#f9a8d4',
        'accent_text': '#be185d',
        'surface_soft': '#fcf7fa',
        'surface_muted': '#f9f1f5',
        'surface_border': '#eed9e3',
        'surface_hover': '#f5e8ef',
        'text_soft': '#6b7280',
        'text_main': '#111827',
    },
    'blue': {
        'label': '蓝',
        'accent_1': '#2563eb',
        'accent_2': '#1d4ed8',
        'accent_soft': '#eff6ff',
        'accent_border': '#93c5fd',
        'accent_text': '#1d4ed8',
        'surface_soft': '#f6f7f9',
        'surface_muted': '#eff1f5',
        'surface_border': '#d7dce5',
        'surface_hover': '#e9edf3',
        'text_soft': '#6b7280',
        'text_main': '#111827',
    },
    'black': {
        'label': '黑',
        'accent_1': '#374151',
        'accent_2': '#111827',
        'accent_soft': '#f3f4f6',
        'accent_border': '#d1d5db',
        'accent_text': '#111827',
        'surface_soft': '#f3f4f6',
        'surface_muted': '#e5e7eb',
        'surface_border': '#d1d5db',
        'surface_hover': '#e5e7eb',
        'text_soft': '#4b5563',
        'text_main': '#111827',
    },
}

LOCALE_OPTIONS = {
    'zh-CN': '中文',
    'en-US': 'English',
}

I18N = {
    'en-US': {
        'platform_title': '💻 OJ Debug Platform',
        'build_version': '1.3',
        'theme_picker': 'Theme',
        'locale_picker': 'Language',
        'logout': 'Log Out',
        'login_or_register': 'Login / Sign Up',
        'guest_user': 'Guest',
        'admin_role': 'Admin',
        'user_role': 'User',
        'not_logged_in': 'Not logged in',
        'login_required': 'Please log in first.',
        'admin_required': 'This page is available to admins only.',
        'return_home': 'Back Home',
        'view_all': 'View All',
        'sample_cases': 'Public Samples',
        'sample_input': 'Sample Input',
        'sample_output': 'Sample Output',
        'sample_explanation': 'Explanation',
        'empty_content': 'No content yet.',
        'login_success': 'Logged in successfully',
        'login_failed': 'Login failed: {reason}',
        'register_failed': 'Sign up failed: {reason}',
        'empty_username_password': 'Username and password are required.',
        'password_mismatch': 'The two passwords do not match.',
        'default_admin': 'Default admin: `admin / admintestpassword`',
        'nav_separator': '  >  ',
        'theme_red': 'Red',
        'theme_pink': 'Pink',
        'theme_blue': 'Blue',
        'theme_black': 'Black',
        'page_home': 'Home Overview',
        'page_problem_detail': 'Problem Detail',
        'page_submission_detail': 'Submission Detail',
        'page_judge': 'Judge',
        'page_problem_admin': 'Problem Admin',
        'page_problemset': 'Problemset',
        'page_submissions': 'Submissions',
        'page_my_submissions': 'My Submissions',
        'page_classes': 'Classes',
        'page_assignments': 'Assignments',
        'page_exams': 'Exams',
        'manage_config': 'Settings',
        'public_samples': 'Public Samples',
        'testcases_data': 'Hidden Testcases',
        'save_problem': 'Save Problem',
        'delete_problem': 'Delete Problem',
        'public_case_detail': 'Expose testcase details',
        'visibility_label': 'Result visibility',
        'visibility_hidden': 'Hidden by default',
        'visibility_after_submit': 'Visible after submission',
        'visibility_public': 'Always visible',
        'allow_input': 'Allow input view',
        'allow_expected': 'Allow expected output view',
        'allow_actual': 'Allow actual output view',
        'allow_error': 'Allow error details view',
        'judge_status_hint': 'Possible language mismatch. The system kept running, but you may want to switch the language and retry.',
    }
}


def get_locale():
    key = st.session_state.get('oj_locale', 'zh-CN')
    return key if key in LOCALE_OPTIONS else 'zh-CN'


def tr(key: str, default: str | None = None, **kwargs):
    locale = get_locale()
    value = I18N.get(locale, {}).get(key, default if default is not None else key)
    if kwargs:
        try:
            return str(value).format(**kwargs)
        except Exception:
            return str(value)
    return str(value)


def get_theme_option_label(key: str):
    labels = {
        'red': tr('theme_red', '红'),
        'pink': tr('theme_pink', '粉'),
        'blue': tr('theme_blue', '蓝'),
        'black': tr('theme_black', '黑'),
    }
    icon = '🎨'
    return f'{icon} {labels.get(key, THEME_OPTIONS.get(key, {}).get("label", key))}'


def get_route_label_map():
    locale = get_locale()
    if locale == 'en-US':
        return ROUTE_LABELS_EN if is_admin() else ROUTE_LABELS_USER_EN
    return ROUTE_LABELS_ZH if is_admin() else ROUTE_LABELS_USER_ZH


def get_theme_key():
    key = st.session_state.get('oj_theme', 'red')
    return key if key in THEME_OPTIONS else 'red'


def get_theme_palette():
    return THEME_OPTIONS[get_theme_key()]


def _current_query_params_dict():
    params = {}
    try:
        for key in list(st.query_params.keys()):
            value = st.query_params.get(key)
            if isinstance(value, (list, tuple)):
                params[str(key)] = str(value[0]) if value else ''
            elif value is not None:
                params[str(key)] = str(value)
    except Exception:
        pass
    return params


def _replace_query_params(params: dict):
    try:
        for key in list(st.query_params.keys()):
            del st.query_params[key]
        for key, value in params.items():
            if value is None or value == '':
                continue
            st.query_params[str(key)] = str(value)
    except Exception:
        pass


def get_query_param(*names, default=''):
    for name in names:
        try:
            value = st.query_params.get(name)
        except Exception:
            value = None
        if isinstance(value, (list, tuple)):
            value = value[0] if value else ''
        if value not in (None, ''):
            return str(value)
    return default


def build_minimal_css():
    theme = get_theme_palette()
    return (
        "<style>\n"
        f" :root {{\n"
        f"  --oj-accent-1: {theme['accent_1']};\n"
        f"  --oj-accent-2: {theme['accent_2']};\n"
        f"  --oj-accent-soft: {theme['accent_soft']};\n"
        f"  --oj-accent-border: {theme['accent_border']};\n"
        f"  --oj-accent-text: {theme['accent_text']};\n"
        f"  --oj-surface-soft: {theme['surface_soft']};\n"
        f"  --oj-surface-muted: {theme['surface_muted']};\n"
        f"  --oj-surface-border: {theme['surface_border']};\n"
        f"  --oj-surface-hover: {theme['surface_hover']};\n"
        f"  --oj-text-soft: {theme['text_soft']};\n"
        f"  --oj-text-main: {theme['text_main']};\n"
        f" }}\n"
        """
 html, body, #root, [data-testid="stApp"] {
  height: auto !important;
  min-height: 100vh !important;
  overflow-x: hidden !important;
  overflow-y: auto !important;
  scroll-behavior: smooth;
}
div[data-testid="stApp"],
.stApp {
  position: static !important;
  inset: auto !important;
  top: auto !important;
  right: auto !important;
  bottom: auto !important;
  left: auto !important;
  width: 100% !important;
  min-height: 100vh !important;
  height: auto !important;
  overflow-x: hidden !important;
  overflow-y: auto !important;
}
header[data-testid="stHeader"] {display:none !important;}
section[data-testid="stSidebar"] {display:none !important;}
div[data-testid="stTopBar"] {display:none !important;}
div[data-testid="stToolbar"] {display:none !important;}
div[data-testid="stDecoration"] {display:none !important;}
div[data-testid="stAppViewContainer"] {
  display: block !important;
  position: static !important;
  inset: auto !important;
  min-height: 100vh !important;
  height: auto !important;
  overflow-x: hidden !important;
  overflow-y: visible !important;
}
div[data-testid="stAppViewContainer"] > div,
div[data-testid="stAppViewContainer"] > section,
div[data-testid="stAppViewContainer"] > main {
  width: 100% !important;
  min-width: 100% !important;
  max-width: 100% !important;
  margin: 0 !important;
  position: static !important;
  inset: auto !important;
  min-height: 100vh !important;
  height: auto !important;
  overflow: visible !important;
}
main,
section[data-testid="stMain"],
div[data-testid="stMain"] {
  width: 100% !important;
  max-width: 100% !important;
  margin: 0 auto !important;
  justify-content: center !important;
  position: static !important;
  inset: auto !important;
  min-height: 100vh !important;
  height: auto !important;
  padding-top: 0 !important;
  overflow: visible !important;
}
main > div,
section[data-testid="stMain"] > div,
div[data-testid="stMain"] > div {
  position: static !important;
  inset: auto !important;
  min-height: 100vh !important;
  height: auto !important;
  overflow: visible !important;
}
div.block-container,
div[data-testid="stMainBlockContainer"] {
  width: 100% !important;
  max-width: 96rem !important;
  margin-left: auto !important;
  margin-right: auto !important;
  box-sizing: border-box;
  min-height: auto !important;
  height: auto !important;
  padding-top: 2.4rem !important;
  padding-bottom: 2rem;
  padding-left: 1.25rem;
  padding-right: 1.25rem;
  overflow: visible !important;
}
div[data-testid="stMainBlockContainer"] > div,
div.block-container > div {
  overflow: visible !important;
}
div[data-testid="stAppViewContainer"]::before{
  content:""; display:block; height:6px; width:100%;
  background:linear-gradient(135deg,var(--oj-accent-1) 0%,var(--oj-accent-2) 100%);
  border-radius:0 0 8px 8px;
}
.oj-nav-wrap,
[data-testid="stVerticalBlock"] > div:first-child {
  scroll-margin-top: 1.25rem;
}
div[data-testid="stVerticalBlock"] {
  gap: 0.85rem !important;
}
.stElementContainer {
  overflow: visible !important;
}
.oj-pill {
  display: inline-block;
  margin: 0 0.35rem 0.35rem 0;
  padding: 0.15rem 0.65rem;
  border-radius: 999px;
  background: var(--oj-surface-muted);
  border: 1px solid var(--oj-surface-border);
  color: var(--oj-text-main);
  font-size: 0.78rem;
  line-height: 1.35;
  white-space: nowrap;
}
.oj-pill.oj-pill-active {
  background: var(--oj-accent-soft);
  border-color: var(--oj-accent-border);
  color: var(--oj-accent-text);
}
.oj-diff-easy {
  background: var(--oj-surface-soft);
  border-color: var(--oj-surface-border);
  color: var(--oj-text-main);
}
.oj-diff-medium {
  background: var(--oj-surface-soft);
  border-color: var(--oj-surface-border);
  color: var(--oj-text-main);
}
.oj-diff-hard {
  background: var(--oj-surface-soft);
  border-color: var(--oj-surface-border);
  color: var(--oj-text-main);
}
.oj-nav-wrap {
  padding: 0.2rem 0 0.35rem 0;
}
.oj-sample-box {
  border: 1px solid var(--oj-surface-border);
  border-radius: 12px;
  padding: 0.75rem 0.9rem;
  background: var(--oj-surface-soft);
  margin-bottom: 0.75rem;
}
.oj-sample-title {
  font-size: 0.82rem;
  color: var(--oj-text-soft);
  margin-bottom: 0.3rem;
}
.oj-sample-text {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.95rem;
  color: var(--oj-text-main);
}
.oj-link-btn {
  display: block;
  width: 100%;
  box-sizing: border-box;
  border-radius: 0.75rem;
  border: 1px solid var(--oj-surface-border);
  background: var(--oj-surface-soft);
  color: var(--oj-text-main) !important;
  text-align: center;
  text-decoration: none !important;
  font-weight: 600;
  line-height: 1.35;
  padding: 0.72rem 0.95rem;
  transition: all 0.15s ease;
}
.oj-link-btn:hover {
  border-color: var(--oj-accent-border);
  background: var(--oj-surface-hover);
}
.oj-link-btn-primary {
  background: linear-gradient(135deg, var(--oj-accent-1) 0%, var(--oj-accent-2) 100%);
  border-color: var(--oj-accent-2);
  color: #ffffff !important;
}
.oj-link-btn-primary:hover {
  background: linear-gradient(135deg, var(--oj-accent-2) 0%, var(--oj-accent-2) 100%);
  border-color: var(--oj-accent-2);
}
[data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-secondary"],
.stButton > button,
div[data-testid="stFormSubmitButton"] > button {
  border-radius: 0.75rem !important;
  border: 1px solid var(--oj-accent-2) !important;
  background: linear-gradient(135deg, var(--oj-accent-1) 0%, var(--oj-accent-2) 100%) !important;
  color: #ffffff !important;
  box-shadow: none !important;
}
[data-testid="stBaseButton-primary"]:hover,
[data-testid="stBaseButton-secondary"]:hover,
.stButton > button:hover,
div[data-testid="stFormSubmitButton"] > button:hover {
  border-color: var(--oj-accent-2) !important;
  filter: brightness(0.96);
}
.stButton > button[kind="secondary"],
div[data-testid="stFormSubmitButton"] > button[kind="secondary"] {
  background: var(--oj-surface-soft) !important;
  color: var(--oj-text-main) !important;
  border: 1px solid var(--oj-surface-border) !important;
}
div[data-testid="stMetric"] {
  background: var(--oj-surface-soft);
  border: 1px solid var(--oj-surface-border);
  border-radius: 14px;
  padding: 0.5rem 0.75rem;
}
div[data-testid="stAlert"] {
  border-radius: 14px !important;
  background: var(--oj-surface-soft) !important;
  border: 1px solid var(--oj-surface-border) !important;
  color: var(--oj-text-main) !important;
}
div[data-testid="stAlert"] * {
  color: var(--oj-text-main) !important;
}
div[data-testid="stDataFrame"] [role="grid"],
div[data-testid="stDataFrame"] [role="table"],
div[data-testid="stDataFrame"] [data-testid="stDataFrameResizable"] {
  background: var(--oj-surface-soft) !important;
  color: var(--oj-text-main) !important;
}
div[data-testid="stDataFrame"] [role="columnheader"],
div[data-testid="stDataFrame"] [role="rowheader"] {
  background: var(--oj-surface-muted) !important;
  color: var(--oj-text-main) !important;
}
div[data-testid="stDataFrame"] [role="gridcell"],
div[data-testid="stDataFrame"] [role="cell"],
div[data-testid="stDataFrame"] [role="row"] {
  background: var(--oj-surface-soft) !important;
  color: var(--oj-text-main) !important;
  border-color: var(--oj-surface-border) !important;
}
div[data-testid="stCodeBlock"],
div[data-testid="stCode"] pre,
div[data-testid="stJson"] pre,
div[data-testid="stJson"] code,
pre {
  background: var(--oj-surface-soft) !important;
  color: var(--oj-text-main) !important;
  border-color: var(--oj-surface-border) !important;
}
table {
  background: var(--oj-surface-soft) !important;
  color: var(--oj-text-main) !important;
}
thead tr,
thead th {
  background: var(--oj-surface-muted) !important;
  color: var(--oj-text-main) !important;
}
tbody tr,
tbody td {
  background: var(--oj-surface-soft) !important;
  color: var(--oj-text-main) !important;
  border-color: var(--oj-surface-border) !important;
}
div[data-testid="stMarkdownContainer"] blockquote,
div[data-testid="stMarkdownContainer"] pre,
div[data-testid="stMarkdownContainer"] code {
  background: var(--oj-surface-soft) !important;
  color: var(--oj-text-main) !important;
  border-color: var(--oj-surface-border) !important;
}
button[data-baseweb="tab"] {
  border-radius: 999px !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
  background: var(--oj-accent-soft) !important;
  color: var(--oj-accent-text) !important;
}
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
textarea {
  border-color: var(--oj-accent-border) !important;
}
div[data-testid="stVerticalBlock"] div[data-baseweb="select"] > div,
div[data-testid="stVerticalBlock"] div[data-baseweb="input"] > div,
div[data-testid="stTextArea"] textarea {
  background: var(--oj-surface-soft) !important;
  color: var(--oj-text-main) !important;
}
input:focus, textarea:focus,
div[data-baseweb="select"] *:focus,
div[data-baseweb="input"] *:focus {
  box-shadow: 0 0 0 1px var(--oj-accent-1) !important;
}
</style>
"""
    )


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
    st.warning(tr('login_required', '请先登录后再使用这个页面。'))


def require_admin_error():
    st.error(tr('admin_required', '只有管理员可以访问这个页面。'))


def clear_problem_cache():
    st.session_state.pop('_all_problems', None)


def page_url(route_key, **query_kwargs):
    slug = ROUTE_TO_SLUG.get(route_key, '')
    base = '/' if not slug else f'/{url_quote(slug)}'
    params = _current_query_params_dict()
    params['theme'] = get_theme_key()
    params['locale'] = get_locale()
    route_identity_keys = {'id', 'assignment_id', 'exam_id', 'class_id', 'submission_id'}
    if route_key in {'home', 'auth', 'classes', 'assignments', 'exams', 'problems', 'submissions', 'users', 'ai', 'ai_config'}:
        for key in route_identity_keys:
            params.pop(key, None)
    for key, value in query_kwargs.items():
        if value is None or value == '':
            continue
        params[str(key)] = str(value)
    if route_key == 'submission_detail':
        sid = params.get('id') or params.get('submission_id')
        if sid:
            params['id'] = str(sid)
            params['submission_id'] = str(sid)
    if not params:
        return base
    return f'{base}?{urlencode(params)}'


def goto(route_key, **query_kwargs):
    page_rel = ROUTE.get(route_key)
    if not page_rel:
        return
    full_url = page_url(route_key, **query_kwargs)
    if route_key == 'submission_detail':
        params = dict(query_kwargs)
        sid = params.get('id') or params.get('submission_id')
        if sid:
            sid = str(sid)
            st.session_state['last_submission_id'] = sid
    st.session_state['pending_goto'] = ('js_navigate', full_url)
    st.rerun()


@st.dialog('登录 / 注册', width='small')
def login_dialog():
    st.caption(tr('default_admin', '默认管理员：`admin / admintestpassword`'))
    mode = st.radio('模式', ['登录', '注册'], horizontal=True, label_visibility='collapsed')
    with st.form('login_register_form'):
        username = st.text_input('用户名')
        password = st.text_input('密码', type='password')
        confirm_password = ''
        if mode == '注册':
            confirm_password = st.text_input('确认密码', type='password')
        submitted = st.form_submit_button('提交', type='primary', use_container_width=True)
    if not submitted:
        return
    if not username.strip() or not password:
        st.warning(tr('empty_username_password', '用户名和密码不能为空'))
        return
    if mode == '注册':
        if password != confirm_password:
            st.warning(tr('password_mismatch', '两次输入的密码不一致'))
            return
        code, data, err = api('POST', '/api/users/', {'username': username.strip(), 'password': password})
        if code != 200:
            st.error(tr('register_failed', '注册失败：{reason}', reason=data.get("msg") if data else err))
            return
    code, data, err = api('POST', '/api/auth/login', {'username': username.strip(), 'password': password})
    if code == 200 and isinstance(data, dict):
        refresh_me()
        toast_safe(tr('login_success', '登录成功'), 'ok')
        st.rerun()
    st.error(tr('login_failed', '登录失败：{reason}', reason=data.get("msg") if data else err))


def render_topbar(page_tag=''):
    user = current_user()
    with st.container(border=True):
        left, middle, build_col, locale_col, theme_col, right = st.columns([4, 2.4, 1.3, 1.8, 2.1, 3])
        with left:
            st.subheader(tr('platform_title', '💻 OJ 调试平台'), divider=False)
        with middle:
            if page_tag:
                st.caption(f'📌 {page_tag}')
        with build_col:
            st.caption(get_build_label())
        with locale_col:
            current_locale = get_locale()
            locale_key = st.selectbox(
                tr('locale_picker', '语言'),
                options=list(LOCALE_OPTIONS.keys()),
                index=list(LOCALE_OPTIONS.keys()).index(current_locale),
                format_func=lambda key: LOCALE_OPTIONS.get(key, key),
                label_visibility='collapsed',
                key='oj_locale_picker',
            )
            if locale_key != current_locale:
                st.session_state['oj_locale'] = locale_key
                params = _current_query_params_dict()
                params['locale'] = locale_key
                params['theme'] = get_theme_key()
                _replace_query_params(params)
                st.rerun()
        with theme_col:
            current_theme = get_theme_key()
            theme_key = st.selectbox(
                tr('theme_picker', '页面配色'),
                options=list(THEME_OPTIONS.keys()),
                index=list(THEME_OPTIONS.keys()).index(current_theme),
                format_func=get_theme_option_label,
                label_visibility='collapsed',
                key='oj_theme_picker',
            )
            if theme_key != current_theme:
                st.session_state['oj_theme'] = theme_key
                params = _current_query_params_dict()
                params['theme'] = theme_key
                params['locale'] = get_locale()
                _replace_query_params(params)
                st.rerun()
        with right:
            if user:
                st.write(f'👤 **{user.get("username", "")}**')
                st.caption(tr('admin_role', '管理员') if is_admin() else tr('user_role', '普通用户'))
                if st.button(tr('logout', '退出登录'), key='topbar_logout', use_container_width=True):
                    api('POST', '/api/auth/logout')
                    st.session_state.pop('oj_me', None)
                    st.session_state.pop(SESSION_COOKIE_NAME, None)
                    st.rerun()
            else:
                st.caption(tr('not_logged_in', '当前未登录'))
                render_page_link(tr('login_or_register', '登录 / 注册'), page_url('auth'), primary=True)


@st.cache_data(show_spinner=False)
def get_build_label():
    default_label = '1.3'
    forced_label = str(os.environ.get('OJ_BUILD_LABEL') or '').strip()
    if forced_label:
        return forced_label
    return default_label


def render_subheader(breadcrumb_parts, active_route='home'):
    label_map = get_route_label_map()
    with st.container():
        st.markdown('<div class="oj-nav-wrap">', unsafe_allow_html=True)
        route_keys = [key for key in ROUTE_ORDER if key in label_map]
        nav_cols = st.columns(len(route_keys))
        for index, route_key in enumerate(route_keys):
            target = page_url(route_key)
            with nav_cols[index]:
                render_page_link(
                    label_map[route_key],
                    target,
                    primary=route_key == active_route,
                )
        crumbs = []
        for index, (text, _) in enumerate(breadcrumb_parts or []):
            crumbs.append(f'**{text}**' if index == len(breadcrumb_parts) - 1 else f':gray[{text}]')
        if crumbs:
            st.caption(tr('nav_separator', '  ›  ').join(crumbs))
        st.markdown('</div>', unsafe_allow_html=True)


def render_home_button(label='返回首页'):
    render_page_link(label or tr('return_home', '返回首页'), page_url('home'))


def render_page_link(label, url, primary=False):
    btn_class = 'oj-link-btn oj-link-btn-primary' if primary else 'oj-link-btn'
    safe_label = html.escape(str(label))
    safe_url = html.escape(str(url), quote=True)
    st.markdown(
        f'<a class="{btn_class}" href="{safe_url}" target="_self">{safe_label}</a>',
        unsafe_allow_html=True,
    )


def _set_pagination_page(state_key, page):
    current = st.session_state.get(state_key)
    normalized_page = max(1, int(page or 1))
    if isinstance(current, dict):
        next_state = dict(current)
        next_state['page'] = normalized_page
        st.session_state[state_key] = next_state
    else:
        st.session_state[state_key] = normalized_page


def render_pagination_controls(state_key, current_page, total_pages, page_size, total_items=None):
    total_pages = max(1, int(total_pages or 1))
    current_page = min(max(1, int(current_page or 1)), total_pages)
    info_parts = [f'当前第 {current_page} / {total_pages} 页', f'每页 {int(page_size or 1)} 条']
    if total_items is not None:
        info_parts.append(f'共 {int(total_items or 0)} 条')

    prev_col, info_col, jump_col, next_col = st.columns([1.2, 2.2, 2.6, 1.2])
    with prev_col:
        if st.button('上一页', key=f'{state_key}_prev', use_container_width=True, disabled=current_page <= 1):
            _set_pagination_page(state_key, current_page - 1)
            st.rerun()
    with info_col:
        st.caption('，'.join(info_parts) + '。')
    with jump_col:
        jump_left, jump_right = st.columns([3, 2])
        with jump_left:
            target_page = st.number_input(
                '跳转页码',
                min_value=1,
                max_value=total_pages,
                value=current_page,
                step=1,
                key=f'{state_key}_jump',
            )
        with jump_right:
            st.write('')
            if st.button('跳转', key=f'{state_key}_go', use_container_width=True):
                _set_pagination_page(state_key, int(target_page))
                st.rerun()
    with next_col:
        if st.button('下一页', key=f'{state_key}_next', use_container_width=True, disabled=current_page >= total_pages):
            _set_pagination_page(state_key, current_page + 1)
            st.rerun()


def render_sample_cases(samples, heading='公开样例'):
    st.markdown(f'#### {heading}')
    if not samples:
        st.info(tr('empty_content', '暂无内容。'))
        return
    for index, sample in enumerate(samples, start=1):
        case_label = f'Case {index}' if get_locale() == 'en-US' else f'样例 {index}'
        st.markdown(f'**{case_label}**')
        col_in, col_out = st.columns(2, gap='small')
        sample_input = '' if sample is None else html.escape(str(sample.get('input', '') or ''))
        sample_output = '' if sample is None else html.escape(str(sample.get('output', '') or sample.get('expected', '') or ''))
        with col_in:
            st.markdown(f'<div class="oj-sample-title">{html.escape(tr("sample_input", "输入样例"))}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="oj-sample-box"><div class="oj-sample-text">{sample_input or "（空）"}</div></div>', unsafe_allow_html=True)
        with col_out:
            st.markdown(f'<div class="oj-sample-title">{html.escape(tr("sample_output", "输出样例"))}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="oj-sample-box"><div class="oj-sample-text">{sample_output or "（空）"}</div></div>', unsafe_allow_html=True)
        explanation = '' if sample is None else str(sample.get('explanation', '') or '')
        if explanation:
            st.caption(f'{tr("sample_explanation", "样例说明")}：{explanation}')


def render_rich_text(content, empty_text='暂无内容。'):
    text = str(content or '').strip()
    if not text:
        st.info(empty_text or tr('empty_content', '暂无内容。'))
        return
    parts = re.split(r'(\$\$.*?\$\$)', text, flags=re.S)
    rendered_any = False
    for part in parts:
        if not part or not part.strip():
            continue
        chunk = part.strip()
        if chunk.startswith('$$') and chunk.endswith('$$'):
            formula = chunk[2:-2].strip()
            if formula:
                st.latex(formula)
                rendered_any = True
        else:
            st.markdown(chunk)
            rendered_any = True
    if not rendered_any:
        st.info(empty_text or tr('empty_content', '暂无内容。'))


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
    try:
        qp_theme = st.query_params.get('theme')
        qp_locale = st.query_params.get('locale')
        if isinstance(qp_theme, (list, tuple)):
            qp_theme = qp_theme[0] if qp_theme else None
        if isinstance(qp_locale, (list, tuple)):
            qp_locale = qp_locale[0] if qp_locale else None
        if qp_theme in THEME_OPTIONS:
            st.session_state['oj_theme'] = qp_theme
        elif st.session_state.get('oj_theme') in THEME_OPTIONS:
            params = _current_query_params_dict()
            params['theme'] = st.session_state['oj_theme']
            _replace_query_params(params)
        else:
            params = _current_query_params_dict()
            params['theme'] = get_theme_key()
            _replace_query_params(params)
        if qp_locale in LOCALE_OPTIONS:
            st.session_state['oj_locale'] = qp_locale
        elif st.session_state.get('oj_locale') in LOCALE_OPTIONS:
            params = _current_query_params_dict()
            params['locale'] = st.session_state['oj_locale']
            _replace_query_params(params)
        else:
            params = _current_query_params_dict()
            params['locale'] = get_locale()
            _replace_query_params(params)
    except Exception:
        pass
    st.markdown(build_minimal_css(), unsafe_allow_html=True)
    pending = st.session_state.pop('pending_goto', None)
    if pending:
        try:
            kind, payload = pending
        except Exception:
            kind, payload = None, None
        if kind == 'js_navigate' and isinstance(payload, str):
            from urllib.parse import urlparse, parse_qs
            try:
                parsed = urlparse(payload)
                query = parse_qs(parsed.query)
                for key in list(st.query_params.keys()):
                    del st.query_params[key]
                for k, vs in query.items():
                    if vs:
                        st.query_params[str(k)] = str(vs[0])
            except Exception:
                pass
            safe_url = html.escape(payload, quote=True)
            st.markdown(
                f'''<meta http-equiv="refresh" content="0; url={safe_url}"><script>window.location.replace("{safe_url}");</script>''',
                unsafe_allow_html=True,
            )
            st.stop()
        else:
            page_path, params = (pending if isinstance(pending, tuple) and len(pending) == 2 else (None, None))
            if page_path:
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
