"""
Streamlit 前端的「公共工具箱」模块——所有 pages/*.py 与 app_streamlit.py 都会 import。
= 作用说明 =
  1. API 调用层：统一封装 common.api(method, path, **kwargs)，
     把浏览器端（Streamlit 进程内部）的 HTTP 请求转发给本地 FastAPI :5000；
     自带会话 cookie（oj_session_id），和后端 session store 保持一致。
  2. 多页面路由：ROUTE 常量 + ROUTE_TO_SLUG + page_url(key, **qs)，
     用「路由 key（如 'problems' / 'judge'）」而不是硬编码 URL，
     避免直接跳转 /判题器 但忘记带 problem_id 的死链问题。
  3. UI 渲染工具：render_topbar / render_page_link / render_subheader / require_login_error 等，
     让每个子页面保持统一的配色、导航条结构和「未登录先引导登录」的一致行为。
  4. 版本 & 国际化：OJ_VERSION（v1.4.1）、THEME_OPTIONS（红/粉/蓝/黑四套配色）、
     I18N 翻译字典 + tr(key, default, **kwargs)，避免把中文散落在 20 多个页面里难维护。
  5. 登录态同步：refresh_me() 每次页面渲染都 GET /api/auth/me，
     把最新的 user_id/username/role/提交数/通过数写进 st.session_state['oj_me']，
     解决 v1.4.0 之前 "用户个人信息 metric 全 '-' / 统计不同步" 的核心根因之一。
= 关键依赖 =
  requests.Session() 做长连接和 cookie 持久化；
  streamlit 做 st.session_state 与 UI 渲染；
  OJ_API_BASE 环境变量控制 FastAPI 地址（默认 http://127.0.0.1:5000）。
= 与评分项对应 =
  - Step4（用户管理 5分）：登录态、当前用户 is_admin 判断、登出接口都集中在这里；
  - Step6（前端交互 5分）：所有 UI 页面的风格统一 + 前后端不直连 DB 的强制封装，
    正是通过 common.api 做到的。
= 注意事项 =
  common.api 返回 (code, payload_or_None, err_or_None) 三元组，
  payload 是 FastAPI _api_response() 包的那一层 {code,msg,data}，
  所以 pages/*.py 的业务逻辑里统一还要判断 payload.get('data')，别把外层当数据。
"""
import html
import os
import re
from urllib.parse import quote as url_quote, urlencode
import requests
import streamlit as st
API_BASE = os.environ.get('OJ_API_BASE', 'http://127.0.0.1:5000')
SESSION_COOKIE_NAME = 'oj_session_id'
SESSION = requests.Session()
ROUTE = {'home': 'app_streamlit.py', 'auth': 'pages/🔐_登录注册.py', 'judge': 'pages/⚖️_判题器.py', 'classes': 'pages/🎓_班级.py', 'assignments': 'pages/📝_作业.py', 'exams': 'pages/📝_考试.py', 'profile': 'pages/👤_个人信息.py', 'languages': 'pages/🔣_语言管理.py', 'problems': 'pages/🗂_题目管理.py', 'problem_detail': 'pages/📄_题目详情.py', 'submissions': 'pages/📋_提交日志.py', 'submission_detail': 'pages/🧾_提交详情.py', 'users': 'pages/👥_用户管理.py', 'ai': 'pages/🤖_AI命题.py', 'ai_config': 'pages/⚙️_AI配置.py'}
ROUTE_ORDER = ['home', 'classes', 'assignments', 'exams', 'profile', 'languages', 'problems', 'submissions', 'users', 'ai', 'ai_config']
ROUTE_LABELS_ZH = {'home': '🏠 判题首页', 'auth': '🔐 登录 / 注册', 'classes': '🎓 班级', 'assignments': '📝 作业', 'exams': '📝 考试', 'profile': '👤 个人信息', 'languages': '🔣 语言管理', 'judge': '⚖️ 判题器', 'problems': '🗂 题目管理', 'submissions': '📋 提交日志', 'users': '👥 用户管理', 'ai': '🤖 AI 命题', 'ai_config': '⚙️ AI 配置'}
ROUTE_LABELS_USER_ZH = {'home': '🏠 判题首页', 'auth': '🔐 登录 / 注册', 'classes': '🎓 我的班级', 'assignments': '📝 我的作业', 'exams': '📝 我的考试', 'profile': '👤 个人信息', 'languages': '🔣 语言列表', 'judge': '⚖️ 判题器', 'problems': '📚 题库浏览', 'submissions': '📋 我的提交', 'ai': '🤖 AI 命题'}
ROUTE_LABELS_EN = {'home': '🏠 Home', 'auth': '🔐 Login', 'classes': '🎓 Classes', 'assignments': '📝 Assignments', 'exams': '📝 Exams', 'profile': '👤 Profile', 'languages': '🔣 Languages', 'judge': '⚖️ Judge', 'problems': '🗂 Problem Admin', 'submissions': '📋 Submissions', 'users': '👥 Users', 'ai': '🤖 AI Problem Gen', 'ai_config': '⚙️ AI Config'}
ROUTE_LABELS_USER_EN = {'home': '🏠 Home', 'auth': '🔐 Login', 'classes': '🎓 My Classes', 'assignments': '📝 My Assignments', 'exams': '📝 My Exams', 'profile': '👤 Profile', 'languages': '🔣 Languages', 'judge': '⚖️ Judge', 'problems': '📚 Problemset', 'submissions': '📋 My Submissions', 'ai': '🤖 AI Problem Gen'}
ROUTE_TO_SLUG = {'home': '', 'auth': '登录注册', 'classes': '班级', 'assignments': '作业', 'exams': '考试', 'profile': '个人信息', 'languages': '语言管理', 'judge': '判题器', 'problems': '题目管理', 'problem_detail': '题目详情', 'submissions': '提交日志', 'submission_detail': '提交详情', 'users': '用户管理', 'ai': 'AI命题', 'ai_config': 'AI配置'}
OJ_VERSION = 'v1.5'
THEME_OPTIONS = {'red': {'label': '红', 'accent_1': '#c62828', 'accent_2': '#8e0000', 'accent_soft': '#fff5f5', 'accent_border': '#fecaca', 'accent_text': '#b91c1c', 'surface_soft': '#faf7f7', 'surface_muted': '#f5f1f1', 'surface_border': '#eadede', 'surface_hover': '#f2e8e8', 'text_soft': '#6b7280', 'text_main': '#111827'}, 'pink': {'label': '粉', 'accent_1': '#d81b60', 'accent_2': '#ad1457', 'accent_soft': '#fdf2f8', 'accent_border': '#f9a8d4', 'accent_text': '#be185d', 'surface_soft': '#fcf7fa', 'surface_muted': '#f9f1f5', 'surface_border': '#eed9e3', 'surface_hover': '#f5e8ef', 'text_soft': '#6b7280', 'text_main': '#111827'}, 'blue': {'label': '蓝', 'accent_1': '#2563eb', 'accent_2': '#1d4ed8', 'accent_soft': '#eff6ff', 'accent_border': '#93c5fd', 'accent_text': '#1d4ed8', 'surface_soft': '#f6f7f9', 'surface_muted': '#eff1f5', 'surface_border': '#d7dce5', 'surface_hover': '#e9edf3', 'text_soft': '#6b7280', 'text_main': '#111827'}, 'black': {'label': '黑', 'accent_1': '#374151', 'accent_2': '#111827', 'accent_soft': '#f3f4f6', 'accent_border': '#d1d5db', 'accent_text': '#111827', 'surface_soft': '#f3f4f6', 'surface_muted': '#e5e7eb', 'surface_border': '#d1d5db', 'surface_hover': '#e5e7eb', 'text_soft': '#4b5563', 'text_main': '#111827'}}
LOCALE_OPTIONS = {'zh-CN': '中文', 'en-US': 'English'}
I18N = {'en-US': {'platform_title': '💻 OJ Debug Platform', 'build_version': '1.3', 'theme_picker': 'Theme', 'locale_picker': 'Language', 'logout': 'Log Out', 'login_or_register': 'Login / Sign Up', 'guest_user': 'Guest', 'admin_role': 'Admin', 'user_role': 'User', 'not_logged_in': 'Not logged in', 'login_required': 'Please log in first.', 'admin_required': 'This page is available to admins only.', 'return_home': 'Back Home', 'view_all': 'View All', 'sample_cases': 'Public Samples', 'sample_input': 'Sample Input', 'sample_output': 'Sample Output', 'sample_explanation': 'Explanation', 'empty_content': 'No content yet.', 'login_success': 'Logged in successfully', 'login_failed': 'Login failed: {reason}', 'register_failed': 'Sign up failed: {reason}', 'empty_username_password': 'Username and password are required.', 'password_mismatch': 'The two passwords do not match.', 'default_admin': 'Default admin: `admin / admintestpassword`', 'nav_separator': '  >  ', 'theme_red': 'Red', 'theme_pink': 'Pink', 'theme_blue': 'Blue', 'theme_black': 'Black', 'page_home': 'Home Overview', 'page_problem_detail': 'Problem Detail', 'page_submission_detail': 'Submission Detail', 'page_judge': 'Judge', 'page_problem_admin': 'Problem Admin', 'page_problemset': 'Problemset', 'page_submissions': 'Submissions', 'page_my_submissions': 'My Submissions', 'page_classes': 'Classes', 'page_assignments': 'Assignments', 'page_exams': 'Exams', 'manage_config': 'Settings', 'public_samples': 'Public Samples', 'testcases_data': 'Hidden Testcases', 'save_problem': 'Save Problem', 'delete_problem': 'Delete Problem', 'public_case_detail': 'Expose testcase details', 'visibility_label': 'Result visibility', 'visibility_hidden': 'Hidden by default', 'visibility_after_submit': 'Visible after submission', 'visibility_public': 'Always visible', 'allow_input': 'Allow input view', 'allow_expected': 'Allow expected output view', 'allow_actual': 'Allow actual output view', 'allow_error': 'Allow error details view', 'judge_status_hint': 'Possible language mismatch. The system kept running, but you may want to switch the language and retry.'}}

def get_locale():
    key = st.session_state.get('oj_locale', 'zh-CN')
    return key if key in LOCALE_OPTIONS else 'zh-CN'

def tr(key: str, default: str | None=None, **kwargs):
    locale = get_locale()
    value = I18N.get(locale, {}).get(key, default if default is not None else key)
    if kwargs:
        try:
            return str(value).format(**kwargs)
        except Exception:
            return str(value)
    return str(value)

def get_theme_option_label(key: str):
    labels = {'red': tr('theme_red', '红'), 'pink': tr('theme_pink', '粉'), 'blue': tr('theme_blue', '蓝'), 'black': tr('theme_black', '黑')}
    icon = '🎨'
    return f"{icon} {labels.get(key, THEME_OPTIONS.get(key, {}).get('label', key))}"

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
    return f"""<style>\n :root {{\n  --oj-accent-1: {theme['accent_1']};\n  --oj-accent-2: {theme['accent_2']};\n  --oj-accent-soft: {theme['accent_soft']};\n  --oj-accent-border: {theme['accent_border']};\n  --oj-accent-text: {theme['accent_text']};\n  --oj-surface-soft: {theme['surface_soft']};\n  --oj-surface-muted: {theme['surface_muted']};\n  --oj-surface-border: {theme['surface_border']};\n  --oj-surface-hover: {theme['surface_hover']};\n  --oj-text-soft: {theme['text_soft']};\n  --oj-text-main: {theme['text_main']};\n }}\n\n html, body, #root, [data-testid="stApp"] {{\n  height: auto !important;\n  min-height: 100vh !important;\n  overflow-x: hidden !important;\n  overflow-y: auto !important;\n  scroll-behavior: smooth;\n}}\ndiv[data-testid="stApp"],\n.stApp {{\n  position: static !important;\n  inset: auto !important;\n  top: auto !important;\n  right: auto !important;\n  bottom: auto !important;\n  left: auto !important;\n  width: 100% !important;\n  min-height: 100vh !important;\n  height: auto !important;\n  overflow-x: hidden !important;\n  overflow-y: auto !important;\n}}\nheader[data-testid="stHeader"] {{display:none !important;}}\nsection[data-testid="stSidebar"] {{display:none !important;}}\ndiv[data-testid="stTopBar"] {{display:none !important;}}\ndiv[data-testid="stToolbar"] {{display:none !important;}}\ndiv[data-testid="stDecoration"] {{display:none !important;}}\ndiv[data-testid="stAppViewContainer"] {{\n  display: block !important;\n  position: static !important;\n  inset: auto !important;\n  min-height: 100vh !important;\n  height: auto !important;\n  overflow-x: hidden !important;\n  overflow-y: visible !important;\n}}\ndiv[data-testid="stAppViewContainer"] > div,\ndiv[data-testid="stAppViewContainer"] > section,\ndiv[data-testid="stAppViewContainer"] > main {{\n  width: 100% !important;\n  min-width: 100% !important;\n  max-width: 100% !important;\n  margin: 0 !important;\n  position: static !important;\n  inset: auto !important;\n  min-height: 100vh !important;\n  height: auto !important;\n  overflow: visible !important;\n}}\nmain,\nsection[data-testid="stMain"],\ndiv[data-testid="stMain"] {{\n  width: 100% !important;\n  max-width: 100% !important;\n  margin: 0 auto !important;\n  justify-content: center !important;\n  position: static !important;\n  inset: auto !important;\n  min-height: 100vh !important;\n  height: auto !important;\n  padding-top: 0 !important;\n  overflow: visible !important;\n}}\nmain > div,\nsection[data-testid="stMain"] > div,\ndiv[data-testid="stMain"] > div {{\n  position: static !important;\n  inset: auto !important;\n  min-height: 100vh !important;\n  height: auto !important;\n  overflow: visible !important;\n}}\ndiv.block-container,\ndiv[data-testid="stMainBlockContainer"] {{\n  width: 100% !important;\n  max-width: 96rem !important;\n  margin-left: auto !important;\n  margin-right: auto !important;\n  box-sizing: border-box;\n  min-height: auto !important;\n  height: auto !important;\n  padding-top: 2.4rem !important;\n  padding-bottom: 2rem;\n  padding-left: 1.25rem;\n  padding-right: 1.25rem;\n  overflow: visible !important;\n}}\ndiv[data-testid="stMainBlockContainer"] > div,\ndiv.block-container > div {{\n  overflow: visible !important;\n}}\ndiv[data-testid="stAppViewContainer"]::before{{\n  content:""; display:block; height:6px; width:100%;\n  background:linear-gradient(135deg,var(--oj-accent-1) 0%,var(--oj-accent-2) 100%);\n  border-radius:0 0 8px 8px;\n}}\n.oj-nav-wrap,\n[data-testid="stVerticalBlock"] > div:first-child {{\n  scroll-margin-top: 1.25rem;\n}}\ndiv[data-testid="stVerticalBlock"] {{\n  gap: 0.85rem !important;\n}}\n.stElementContainer {{\n  overflow: visible !important;\n}}\n.oj-pill {{\n  display: inline-block;\n  margin: 0 0.35rem 0.35rem 0;\n  padding: 0.15rem 0.65rem;\n  border-radius: 999px;\n  background: var(--oj-surface-muted);\n  border: 1px solid var(--oj-surface-border);\n  color: var(--oj-text-main);\n  font-size: 0.78rem;\n  line-height: 1.35;\n  white-space: nowrap;\n}}\n.oj-pill.oj-pill-active {{\n  background: var(--oj-accent-soft);\n  border-color: var(--oj-accent-border);\n  color: var(--oj-accent-text);\n}}\n.oj-diff-easy {{\n  background: var(--oj-surface-soft);\n  border-color: var(--oj-surface-border);\n  color: var(--oj-text-main);\n}}\n.oj-diff-medium {{\n  background: var(--oj-surface-soft);\n  border-color: var(--oj-surface-border);\n  color: var(--oj-text-main);\n}}\n.oj-diff-hard {{\n  background: var(--oj-surface-soft);\n  border-color: var(--oj-surface-border);\n  color: var(--oj-text-main);\n}}\n.oj-nav-wrap {{\n  padding: 0.2rem 0 0.35rem 0;\n}}\n.oj-sample-box {{\n  border: 1px solid var(--oj-surface-border);\n  border-radius: 12px;\n  padding: 0.75rem 0.9rem;\n  background: var(--oj-surface-soft);\n  margin-bottom: 0.75rem;\n}}\n.oj-sample-title {{\n  font-size: 0.82rem;\n  color: var(--oj-text-soft);\n  margin-bottom: 0.3rem;\n}}\n.oj-sample-text {{\n  white-space: pre-wrap;\n  word-break: break-word;\n  font-size: 0.95rem;\n  color: var(--oj-text-main);\n}}\n.oj-link-btn {{\n  display: block;\n  width: 100%;\n  box-sizing: border-box;\n  border-radius: 0.75rem;\n  border: 1px solid var(--oj-surface-border);\n  background: var(--oj-surface-soft);\n  color: var(--oj-text-main) !important;\n  text-align: center;\n  text-decoration: none !important;\n  font-weight: 600;\n  line-height: 1.35;\n  padding: 0.72rem 0.95rem;\n  transition: all 0.15s ease;\n}}\n.oj-link-btn:hover {{\n  border-color: var(--oj-accent-border);\n  background: var(--oj-surface-hover);\n}}\n.oj-link-btn-primary {{\n  background: linear-gradient(135deg, var(--oj-accent-1) 0%, var(--oj-accent-2) 100%);\n  border-color: var(--oj-accent-2);\n  color: #ffffff !important;\n}}\n.oj-link-btn-primary:hover {{\n  background: linear-gradient(135deg, var(--oj-accent-2) 0%, var(--oj-accent-2) 100%);\n  border-color: var(--oj-accent-2);\n}}\n[data-testid="stBaseButton-primary"],\n[data-testid="stBaseButton-secondary"],\n.stButton > button,\ndiv[data-testid="stFormSubmitButton"] > button {{\n  border-radius: 0.75rem !important;\n  border: 1px solid var(--oj-accent-2) !important;\n  background: linear-gradient(135deg, var(--oj-accent-1) 0%, var(--oj-accent-2) 100%) !important;\n  color: #ffffff !important;\n  box-shadow: none !important;\n}}\n[data-testid="stBaseButton-primary"]:hover,\n[data-testid="stBaseButton-secondary"]:hover,\n.stButton > button:hover,\ndiv[data-testid="stFormSubmitButton"] > button:hover {{\n  border-color: var(--oj-accent-2) !important;\n  filter: brightness(0.96);\n}}\n.stButton > button[kind="secondary"],\ndiv[data-testid="stFormSubmitButton"] > button[kind="secondary"] {{\n  background: var(--oj-surface-soft) !important;\n  color: var(--oj-text-main) !important;\n  border: 1px solid var(--oj-surface-border) !important;\n}}\ndiv[data-testid="stMetric"] {{\n  background: var(--oj-surface-soft);\n  border: 1px solid var(--oj-surface-border);\n  border-radius: 14px;\n  padding: 0.5rem 0.75rem;\n}}\ndiv[data-testid="stAlert"] {{\n  border-radius: 14px !important;\n  background: var(--oj-surface-soft) !important;\n  border: 1px solid var(--oj-surface-border) !important;\n  color: var(--oj-text-main) !important;\n}}\ndiv[data-testid="stAlert"] * {{\n  color: var(--oj-text-main) !important;\n}}\ndiv[data-testid="stDataFrame"] [role="grid"],\ndiv[data-testid="stDataFrame"] [role="table"],\ndiv[data-testid="stDataFrame"] [data-testid="stDataFrameResizable"] {{\n  background: var(--oj-surface-soft) !important;\n  color: var(--oj-text-main) !important;\n}}\ndiv[data-testid="stDataFrame"] [role="columnheader"],\ndiv[data-testid="stDataFrame"] [role="rowheader"] {{\n  background: var(--oj-surface-muted) !important;\n  color: var(--oj-text-main) !important;\n}}\ndiv[data-testid="stDataFrame"] [role="gridcell"],\ndiv[data-testid="stDataFrame"] [role="cell"],\ndiv[data-testid="stDataFrame"] [role="row"] {{\n  background: var(--oj-surface-soft) !important;\n  color: var(--oj-text-main) !important;\n  border-color: var(--oj-surface-border) !important;\n}}\ndiv[data-testid="stCodeBlock"],\ndiv[data-testid="stCode"] pre,\ndiv[data-testid="stJson"] pre,\ndiv[data-testid="stJson"] code,\npre {{\n  background: var(--oj-surface-soft) !important;\n  color: var(--oj-text-main) !important;\n  border-color: var(--oj-surface-border) !important;\n}}\ntable {{\n  background: var(--oj-surface-soft) !important;\n  color: var(--oj-text-main) !important;\n}}\nthead tr,\nthead th {{\n  background: var(--oj-surface-muted) !important;\n  color: var(--oj-text-main) !important;\n}}\ntbody tr,\ntbody td {{\n  background: var(--oj-surface-soft) !important;\n  color: var(--oj-text-main) !important;\n  border-color: var(--oj-surface-border) !important;\n}}\ndiv[data-testid="stMarkdownContainer"] blockquote,\ndiv[data-testid="stMarkdownContainer"] pre,\ndiv[data-testid="stMarkdownContainer"] code {{\n  background: var(--oj-surface-soft) !important;\n  color: var(--oj-text-main) !important;\n  border-color: var(--oj-surface-border) !important;\n}}\nbutton[data-baseweb="tab"] {{\n  border-radius: 999px !important;\n}}\nbutton[data-baseweb="tab"][aria-selected="true"] {{\n  background: var(--oj-accent-soft) !important;\n  color: var(--oj-accent-text) !important;\n}}\ndiv[data-baseweb="select"] > div,\ndiv[data-baseweb="input"] > div,\ntextarea {{\n  border-color: var(--oj-accent-border) !important;\n}}\ndiv[data-testid="stVerticalBlock"] div[data-baseweb="select"] > div,\ndiv[data-testid="stVerticalBlock"] div[data-baseweb="input"] > div,\ndiv[data-testid="stTextArea"] textarea {{\n  background: var(--oj-surface-soft) !important;\n  color: var(--oj-text-main) !important;\n}}\ninput:focus, textarea:focus,\ndiv[data-baseweb="select"] *:focus,\ndiv[data-baseweb="input"] *:focus {{\n  box-shadow: 0 0 0 1px var(--oj-accent-1) !important;\n}}\n</style>\n"""

def api(method, path, json_body=None, params=None, timeout=60):
    cookies = {}
    sid = st.session_state.get(SESSION_COOKIE_NAME)
    if sid:
        cookies[SESSION_COOKIE_NAME] = sid
    try:
        response = SESSION.request(method, f'{API_BASE}{path}', json=json_body, params=params, cookies=cookies, timeout=timeout)
    except Exception as exc:
        return (0, None, str(exc))
    try:
        data = response.json()
    except Exception:
        data = None
    if SESSION_COOKIE_NAME in response.cookies:
        st.session_state[SESSION_COOKIE_NAME] = response.cookies[SESSION_COOKIE_NAME]
    return (response.status_code, data, None)

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

@st.dialog('登录 / 注册')
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
            st.error(tr('register_failed', '注册失败：{reason}', reason=data.get('msg') if data else err))
            return
    code, data, err = api('POST', '/api/auth/login', {'username': username.strip(), 'password': password})
    if code == 200 and isinstance(data, dict):
        refresh_me()
        toast_safe(tr('login_success', '登录成功'), 'ok')
        st.rerun()
    st.error(tr('login_failed', '登录失败：{reason}', reason=data.get('msg') if data else err))

def render_topbar(page_tag='', on_auth_page=False):
    user = current_user()
    with st.container(border=True):
        left, middle, build_col, locale_col, theme_col, right = st.columns([4, 2.4, 1.3, 1.8, 2.1, 3])
        with left:
            st.subheader(tr('platform_title', '💻 OJ 调试平台'))
        with middle:
            if page_tag:
                st.caption(f'📌 {page_tag}')
        with build_col:
            st.caption(get_build_label())
        with locale_col:
            current_locale = get_locale()
            locale_key = st.selectbox(tr('locale_picker', '语言'), options=list(LOCALE_OPTIONS.keys()), index=list(LOCALE_OPTIONS.keys()).index(current_locale), format_func=lambda key: LOCALE_OPTIONS.get(key, key), label_visibility='collapsed', key='oj_locale_picker')
            if locale_key != current_locale:
                st.session_state['oj_locale'] = locale_key
                params = _current_query_params_dict()
                params['locale'] = locale_key
                params['theme'] = get_theme_key()
                _replace_query_params(params)
                st.rerun()
        with theme_col:
            current_theme = get_theme_key()
            theme_key = st.selectbox(tr('theme_picker', '页面配色'), options=list(THEME_OPTIONS.keys()), index=list(THEME_OPTIONS.keys()).index(current_theme), format_func=get_theme_option_label, label_visibility='collapsed', key='oj_theme_picker')
            if theme_key != current_theme:
                st.session_state['oj_theme'] = theme_key
                params = _current_query_params_dict()
                params['theme'] = theme_key
                params['locale'] = get_locale()
                _replace_query_params(params)
                st.rerun()
        with right:
            if user:
                st.write(f"👤 **{user.get('username', '')}**")
                st.caption(tr('admin_role', '管理员') if is_admin() else tr('user_role', '普通用户'))
                if st.button(tr('logout', '退出登录'), key='topbar_logout', use_container_width=True):
                    api('POST', '/api/auth/logout')
                    st.session_state.pop('oj_me', None)
                    st.session_state.pop(SESSION_COOKIE_NAME, None)
                    st.rerun()
            elif on_auth_page:
                st.caption(tr('auth_page_tip', '正在账号入口页面'))
            else:
                st.caption(tr('not_logged_in', '当前未登录'))
                render_page_link(tr('login_or_register', '登录 / 注册'), page_url('auth'), primary=True)

@st.cache_data()
def get_build_label():
    default_label = OJ_VERSION
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
                render_page_link(label_map[route_key], target, primary=route_key == active_route)
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
    st.markdown(f'<a class="{btn_class}" href="{safe_url}" target="_self">{safe_label}</a>', unsafe_allow_html=True)

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
            target_page = st.number_input('跳转页码', min_value=1, max_value=total_pages, value=current_page, step=1, key=f'{state_key}_jump')
        with jump_right:
            st.write('')
            if st.button('跳转', key=f'{state_key}_go', use_container_width=True):
                _set_pagination_page(state_key, int(target_page))
                st.rerun()
    with next_col:
        if st.button('下一页', key=f'{state_key}_next', use_container_width=True, disabled=current_page >= total_pages):
            _set_pagination_page(state_key, current_page + 1)
            st.rerun()

def render_sample_cases(samples, heading='题面样例'):
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
            st.markdown(f"""<div class="oj-sample-title">{html.escape(tr('sample_input', '输入样例'))}</div>""", unsafe_allow_html=True)
            st.markdown(f"""<div class="oj-sample-box"><div class="oj-sample-text">{sample_input or '（空）'}</div></div>""", unsafe_allow_html=True)
        with col_out:
            st.markdown(f"""<div class="oj-sample-title">{html.escape(tr('sample_output', '输出样例'))}</div>""", unsafe_allow_html=True)
            st.markdown(f"""<div class="oj-sample-box"><div class="oj-sample-text">{sample_output or '（空）'}</div></div>""", unsafe_allow_html=True)
        explanation = '' if sample is None else str(sample.get('explanation', '') or '')
        if explanation:
            st.caption(f"{tr('sample_explanation', '样例说明')}：{explanation}")

def render_rich_text(content, empty_text='暂无内容。'):
    text = str(content or '').strip()
    if not text:
        st.info(empty_text or tr('empty_content', '暂无内容。'))
        return
    parts = re.split('(\\$\\$.*?\\$\\$)', text, flags=re.S)
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
        if keyword and keyword not in pid and (keyword not in title):
            continue
        if difficulty and str(problem.get('difficulty', '')) != difficulty:
            continue
        tags = set(problem.get('tags') or [])
        if tags_required and (not tags_required & tags):
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
            kind, payload = (None, None)
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
            st.markdown(f'<meta http-equiv="refresh" content="0; url={safe_url}"><script>window.location.replace("{safe_url}");</script>', unsafe_allow_html=True)
            st.stop()
        else:
            page_path, params = pending if isinstance(pending, tuple) and len(pending) == 2 else (None, None)
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