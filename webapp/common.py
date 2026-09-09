# -*- coding: utf-8 -*-
"""
OJ Streamlit MPA 公共模块（原生组件版本，≤300 行，非结构型 CSS≤120 行）
"""
import os, sys, json, time
from urllib.parse import quote as _quote
import requests
import streamlit as st

API_BASE = 'http://127.0.0.1:5000'
if os.environ.get('OJ_API_BASE'):
    API_BASE = os.environ['OJ_API_BASE']

ROUTE = {
    'home':        'app_streamlit',
    'judge':       'pages/⚖️_判题器.py',
    'submissions': 'pages/📋_提交日志.py',
    'classes':     'pages/🎓_班级.py',
    'assignments': 'pages/📚_作业.py',
    'exams':       'pages/📝_考试.py',
    'problems':    'pages/🗂_题目管理.py',
    'users':       'pages/👥_用户管理.py',
    'ai':          'pages/🤖_AI命题.py',
    'ai_config':   'pages/⚙️_AI配置.py',
}
ROUTE_ORDER = ['home', 'submissions', 'classes', 'assignments', 'exams', 'problems', 'users', 'ai', 'ai_config']
ROUTE_LABELS = {
    'home': '🏠 判题首页', 'submissions': '📋 提交日志',
    'classes': '🎓 班级管理', 'assignments': '📚 作业中心',
    'exams': '📝 考试中心', 'problems': '🗂 题目管理',
    'users': '👥 用户管理', 'ai': '🤖 AI中心',
    'ai_config': '⚙️ AI配置',
}
ROUTE_LABELS_USER = {
    'home': '🏠 判题首页', 'submissions': '📋 我的提交',
    'classes': '🎓 我的班级', 'assignments': '📚 我的作业',
    'exams': '📝 我的考试',
}

MINIMAL_CSS = """
<style>
header[data-testid=stHeader] {display:none !important;}
section[data-testid=stSidebar] {display:none !important;}
div.block-container {padding-top: 0rem; padding-bottom: 3rem; max-width: 95rem;}
div[data-testid=stTopBar] {display:none !important;}
div[data-testid="stAppViewContainer"]::before {
  content: ""; display: block; height: 6px; width: 100%;
  background: linear-gradient(135deg, #c62828 0%, #8e0000 100%);
  border-radius: 0 0 6px 6px;
}
.status-AC {color:#15803d; font-weight:700;}
.status-WA,.status-RE,.status-CE,.status-SE,.status-MLE {color:#b91c1c; font-weight:700;}
.status-TLE,.status-OLE,.status-PENDING,.status-RUNNING,.status-JUDGING {color:#a16207; font-weight:700;}
.footer-text {text-align:center; color:#6b7280; font-size:12.5px; margin-top:3rem; padding-top:1rem; border-top:1px solid #e5e7eb;}
</style>
"""

ROUTE_TO_SLUG = {
    'home':        '',
    'judge':       '判题器',
    'submissions': '提交日志',
    'classes':     '班级',
    'assignments': '作业',
    'exams':       '考试',
    'problems':    '题目管理',
    'users':       '用户管理',
    'ai':          'AI命题',
    'ai_config':   'AI配置',
}

SES = requests.Session()

def api(method, path, json_body=None, params=None, timeout=60):
    cookies = {}
    sid = st.session_state.get('oj_session_id')
    if sid:
        cookies['oj_session_id'] = sid
    url = f'{API_BASE}{path}'
    try:
        r = SES.request(method, url, json=json_body, params=params,
                        cookies=cookies, timeout=timeout)
    except Exception as e:
        return 0, None, str(e)
    try:
        data = r.json()
    except Exception:
        data = {}
    for k, v in r.cookies.items():
        if k == 'oj_session_id':
            st.session_state['oj_session_id'] = v
    return r.status_code, data, None

def refresh_me():
    code, data, _ = api('GET', '/api/users/me')
    if code == 200 and isinstance(data, dict) and data.get('data'):
        st.session_state['oj_me'] = data['data']
    elif code == 401:
        st.session_state.pop('oj_me', None)
        st.session_state.pop('oj_session_id', None)
    return st.session_state.get('oj_me')

def current_user():
    return st.session_state.get('oj_me')

def is_admin():
    u = current_user()
    return bool(u) and str(u.get('role', '')).lower() == 'admin'

def require_login_error():
    st.warning('🔐 请先登录后使用此功能。点击右上角「🔐 登录 / 注册」按钮登录。')

def require_admin_error():
    st.error('⛔ 需要管理员权限才能访问此页面。')

def goto(route_key, **query_kwargs):
    page_rel = ROUTE.get(route_key)
    if not page_rel:
        return
    qp = {}
    for k, v in query_kwargs.items():
        if v is None:
            continue
        qp[k] = '1' if v is True else ('0' if v is False else str(v))
    st.session_state['pending_goto'] = (route_key, page_rel, qp)
    st.rerun()

def toast_safe(msg, kind='info'):
    icon = {'ok':'✅','info':'ℹ️','warn':'⚠️','err':'❌'}.get(kind, 'ℹ️')
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

@st.dialog('用户登录 / 注册', width='small')
def login_dialog():
    st.caption('默认管理员账号：`admin / admintestpassword`')
    mode = st.radio('模式', ['🔐 登录', '📝 注册'], horizontal=True, label_visibility='collapsed')
    with st.form('login_register_form', clear_on_submit=False):
        u = st.text_input('用户名', placeholder='3-40 字符')
        p = st.text_input('密码', type='password', placeholder='至少 6 位')
        submitted = st.form_submit_button('提交', type='primary', use_container_width=True)
    if submitted:
        if not u or not p:
            st.warning('请填写用户名和密码')
            return
        if mode.startswith('📝'):
            c, d, err = api('POST', '/api/users/', {'username': u, 'password': p})
            if c != 200:
                st.error(f'注册失败：{d.get("msg") if d else err}')
                return
        c, d, err = api('POST', '/api/auth/login', {'username': u, 'password': p})
        if c == 200 and d and d.get('data'):
            refresh_me()
            toast_safe('登录成功', 'ok')
            st.rerun()
        else:
            st.error(f'登录失败：{d.get("msg") if d else err}')

def inject_minimal_css():
    # 样式注入（仅做非结构性统一样式隐藏 header/sidebar/status color）
    st.markdown(MINIMAL_CSS, unsafe_allow_html=True)

def ensure_init():
    # 处理待跳转：用 Streamlit 原生 st.switch_page(params=...) 保持 URL 带参数 + 保留会话状态（1.63+ 原生支持）
    # page 必须用相对路径（如 "app_streamlit.py" 或 "pages/X.py"），否则 params 不会写入浏览器 URL
    pending = st.session_state.pop('pending_goto', None)
    if pending:
        route_key, page_rel, qp = pending
        page_path = page_rel if route_key != 'home' else 'app_streamlit.py'
        params = {}
        for k, v in (qp or {}).items():
            params[str(k)] = str(v)
        try:
            st.switch_page(page_path, params=params)
        except TypeError:
            # 老版本兼容：逐字段写 st.query_params 后 switch_page（相对路径）
            try:
                for k in list(st.query_params.keys()):
                    if k not in params:
                        del st.query_params[k]
            except Exception:
                pass
            for k, v in (params or {}).items():
                st.query_params[k] = v
            st.switch_page(page_path)
        return
    inject_minimal_css()
    refresh_me()

def render_topbar(page_tag=''):
    u = current_user()
    top = st.container(border=True)
    with top:
        col1, col2, col3 = st.columns([4, 4, 4])
        with col1:
            st.subheader('💻 OJ 调试平台', divider=False)
        with col2:
            if page_tag:
                st.caption(f'📌 {page_tag}')
        with col3:
            if u:
                st.write(f'👤 **{u.get("username")}**')
                if is_admin():
                    st.caption('🛡 管理员')
                if st.button('🚪 登出', use_container_width=True, key='topbar_logout'):
                    api('POST', '/api/auth/logout')
                    st.session_state.pop('oj_me', None)
                    st.session_state.pop('oj_session_id', None)
                    st.rerun()
            else:
                st.caption('游客状态')
                if st.button('🔐 登录 / 注册', use_container_width=True, type='primary', key='topbar_login'):
                    login_dialog()

def render_subheader(breadcrumb_parts, active_route='home'):
    u = current_user()
    bar = st.container()
    with bar:
        c1, c2 = st.columns([2, 3])
        with c1:
            text_parts = []
            for i, (name, route_key) in enumerate(breadcrumb_parts or []):
                is_last = i == len(breadcrumb_parts) - 1
                text_parts.append(f'**{name}**' if is_last else f':gray[{name}]')
            st.caption('  ›  '.join(text_parts) if text_parts else ROUTE_LABELS.get(active_route, ''))
        with c2:
            label_map = ROUTE_LABELS if is_admin() else ROUTE_LABELS_USER
            order = [r for r in ROUTE_ORDER if r in label_map]
            per_row = len(order)
            cols = st.columns(per_row)
            for idx, rk in enumerate(order):
                with cols[idx]:
                    active = (rk == active_route)
                    lbl = label_map.get(rk, rk)
                    slug = ROUTE_TO_SLUG.get(rk, '')
                    if slug == '':
                        url = '/'
                    else:
                        url = '/' + _quote(slug)
                    st.link_button(lbl, url, use_container_width=True,
                                   type='primary' if active else 'secondary',
                                   key=f'subhdr_{rk}_{active_route}')

def load_all_problems(force=False):
    if not force and '_all_problems' in st.session_state and st.session_state['_all_problems']:
        return st.session_state['_all_problems']
    code, data, _ = api('GET', '/api/problems/')
    lst = []
    if code == 200 and isinstance(data, dict):
        d = data.get('data')
        if isinstance(d, list):
            lst = d
        elif isinstance(d, dict):
            lst = d.get('list') or d.get('problems') or d.get('items') or []
    if lst and 'description' not in (lst[0] or {}):
        full = []
        for b in lst:
            c2, d2, _ = api('GET', f"/api/problems/{b.get('id','')}")
            full.append(d2['data'] if (c2 == 200 and d2 and d2.get('data')) else b)
        lst = full
    if lst:
        st.session_state['_all_problems'] = lst
    return lst

def get_filtered_problems(problems, keyword='', difficulty='', active_tags=None):
    active_tags = set(active_tags or [])
    kw = (keyword or '').lower()
    out = []
    for p in problems:
        if kw and kw not in str(p.get('id','')).lower() and kw not in str(p.get('title','')).lower():
            continue
        if difficulty and str(p.get('difficulty','')) != difficulty:
            continue
        if active_tags:
            tags = set(p.get('tags') or [])
            if not (active_tags & tags):
                continue
        out.append(p)
    return out
