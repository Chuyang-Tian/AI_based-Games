# -*- coding: utf-8 -*-
"""
提交日志（Streamlit 原生组件版，dataframe 表格 + 筛选）
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import pandas as pd

st.set_page_config(page_title='提交日志 · OJ', page_icon='📋', layout='wide',
                   initial_sidebar_state='collapsed')

from common import (
    ensure_init, render_topbar, render_subheader,
    current_user, require_login_error, is_admin, is_teacher,
    api, toast_safe, goto, load_all_problems,
)

ensure_init()
render_topbar('历史提交记录')
render_subheader([('🏠 判题首页', 'home'), ('📋 提交日志', None)], 'submissions')

user = current_user()
if not user:
    require_login_error()
    st.stop()

problems = load_all_problems()
id_to_title = {p.get('id'): p.get('title') for p in problems}

PAGE_SIZE = 50

if 'sub_page' not in st.session_state:
    st.session_state['sub_page'] = 1
if 'sub_filters' not in st.session_state:
    st.session_state['sub_filters'] = {
        'problem_id': '', 'status': '', 'lang': '',
        'user_id_or_username': '',
        'mine': True,
    }

filters = st.session_state['sub_filters']

# 顶部筛选条（原生表单）
filter_box = st.container(border=True)
with filter_box:
    with st.form('sub_filter_form', clear_on_submit=False):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            f_pid = st.text_input('题目 ID', value=filters.get('problem_id', ''))
        with c2:
            statuses = ['', 'AC', 'WA', 'TLE', 'MLE', 'OLE', 'RE', 'CE', 'SE', 'PE']
            f_st = st.selectbox('状态', statuses, index=statuses.index(filters.get('status','')))
        with c3:
            f_lang = st.text_input('语言（如 python/cpp/java/js）', value=filters.get('lang', ''))
        with c4:
            f_uid = st.text_input('用户 ID / 用户名（管理员/老师可查他人）',
                                  value=filters.get('user_id_or_username', ''),
                                  disabled=(not is_admin() and not is_teacher()))
        m1, m2, m3 = st.columns([3, 4, 4])
        with m1:
            f_mine = st.checkbox('只看我自己的提交', value=filters.get('mine', True))
        with m2:
            submitted = st.form_submit_button('🔍 筛选查询', type='primary', use_container_width=True)
        with m3:
            reset = st.form_submit_button('🔄 重置筛选', use_container_width=True)
    if submitted:
        filters['problem_id'] = f_pid
        filters['status'] = f_st
        filters['lang'] = f_lang
        filters['user_id_or_username'] = f_uid if (is_admin() or is_teacher()) else ''
        filters['mine'] = f_mine
        st.session_state['sub_filters'] = filters
        st.session_state['sub_page'] = 1
        st.rerun()
    if reset:
        st.session_state['sub_filters'] = {
            'problem_id': '', 'status': '', 'lang': '',
            'user_id_or_username': '', 'mine': True,
        }
        st.session_state['sub_page'] = 1
        st.rerun()

# 查询
params = {'limit': PAGE_SIZE + 1, 'page': st.session_state['sub_page']}
if filters.get('problem_id'):
    params['problem_id'] = filters['problem_id']
if filters.get('status'):
    params['status'] = filters['status']
if filters.get('lang'):
    params['language'] = filters['lang']
if filters.get('user_id_or_username') and (is_admin() or is_teacher()):
    params['user_id_or_username'] = filters['user_id_or_username']
elif filters.get('mine') and user:
    try:
        params['user_id_or_username'] = str(user.get('id') or user.get('username'))
    except Exception:
        pass

c, d, err = api('GET', '/api/submissions/', params=params)
rows = []
total_displayed = 0
has_next = False
if c == 200 and isinstance(d, dict) and isinstance(d.get('data'), list):
    data = d['data']
    has_next = len(data) > PAGE_SIZE
    data = data[:PAGE_SIZE]
    total_displayed = len(data)
    for s in data:
        rows.append({
            'ID': s.get('id'),
            '题目 ID': s.get('problem_id'),
            '题目标题': id_to_title.get(s.get('problem_id'), s.get('problem_id') or ''),
            '状态': s.get('status') or '--',
            '得分': s.get('score', 0),
            '语言': s.get('language') or '',
            '用户 ID': s.get('user_id'),
            '用户名': s.get('username') or '',
            '用时 ms': s.get('time_ms', 0),
            '内存 KB': s.get('memory_kb', 0),
            '提交时间': s.get('created_at') or s.get('submit_time') or '',
        })

top_stats = st.container(border=True)
with top_stats:
    a, b, cc, dd = st.columns(4)
    a.metric('当前页条数', f'{total_displayed}')
    b.metric('AC 数', f'{sum(1 for r in rows if r["状态"] == "AC")}')
    cc.metric('WA 数', f'{sum(1 for r in rows if r["状态"] == "WA")}')
    dd.metric('当前筛选页码', f'#{st.session_state["sub_page"]}')

st.subheader('📋 历史提交（点击行或查看详情按钮查看逐测试点结果）', divider=False)

if not rows:
    st.info('（暂无匹配的提交记录）')
else:
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True, height=480,
                 column_order=['ID', '题目 ID', '题目标题', '状态', '得分', '语言',
                               '用户 ID', '用户名', '用时 ms', '内存 KB', '提交时间'])

    # 查看详情（selectbox 输入 Submission ID）
    with st.container(border=True):
        with st.form('view_detail_form', clear_on_submit=False):
            c1, c2 = st.columns([5, 3])
            with c1:
                options = [f'#{r["ID"]}  |  {r["状态"]}  |  PID={r["题目 ID"]}  |  {r["题目标题"][:28]}' for r in rows]
                if options:
                    picked = st.selectbox('选择一个提交查看详情（默认第一条）', options, index=0)
                    pick_idx = options.index(picked)
                    picked_id = rows[pick_idx]['ID']
                else:
                    picked_id = st.text_input('Submission ID', '')
            with c2:
                st.caption('')
                sbm = st.form_submit_button('🔎 查看详情 / 跳转判题页', type='primary', use_container_width=True)
        if sbm and picked_id:
            # 跳转判题页（带上 submission 参数）
            pid_choice = next((r['题目 ID'] for r in rows if str(r['ID']) == str(picked_id)), None)
            if pid_choice:
                goto('judge', id=str(pid_choice), submission=str(picked_id))
            else:
                # 只带 submission 也能进入判题详情（若没有 pid 判题页会 fallback 载入）
                # 为保险起见：直接在本页 render 详情
                st.info(f'加载 Submission #{picked_id} 的详情...')
                c, d, _ = api('GET', f'/api/submissions/{picked_id}')
                if c == 200 and d and d.get('data'):
                    sub = d['data']
                    perm = int(sub.get('perm_mask') or 0)
                    cases = (sub.get('details') or sub.get('case_results') or
                             sub.get('cases') or [])
                    if not isinstance(cases, list):
                        try:
                            raw = sub.get('detail') or sub.get('extra') or '{}'
                            if isinstance(raw, str):
                                raw = json.loads(raw)
                            if isinstance(raw, dict):
                                cases = raw.get('case_results') or raw.get('cases') or raw.get('details') or []
                        except Exception:
                            cases = []
                    cols = st.columns(4)
                    cols[0].metric('状态', str(sub.get('status') or '--'))
                    cols[1].metric('得分', f'{sub.get("score",0)} / {sub.get("total_cases",0)*10 if sub.get("total_cases",0) else 100}')
                    cols[2].metric('用时 ms', f'{sub.get("time_ms",0)}')
                    cols[3].metric('内存 KB', f'{sub.get("memory_kb",0)}')
                    st.code(sub.get('code') or '(无权查看代码)', language=None if perm & 0x10 else None)
                    st.markdown('#### 逐测试点')
                    for i, cs in enumerate(cases or []):
                        if not isinstance(cs, dict):
                            continue
                        with st.expander(
                            f'#{i+1} [{cs.get("status") or cs.get("result") or "??"}]  ⏱ {cs.get("time_ms",0)}ms · 💾 {round((cs.get("memory_kb",0) or 0)/1024,2)}MB',
                            expanded=(cs.get('status') not in ('AC',))
                        ):
                            a, b = st.columns(2)
                            with a:
                                if cs.get('input') is not None and (perm & 1):
                                    st.caption('🔤 Input')
                                    st.code(cs.get('input'), language=None)
                                else:
                                    st.info('🔒 无权查看 Input')
                            with b:
                                if cs.get('stderr') or cs.get('error'):
                                    st.caption('❌ 错误')
                                    st.code(cs.get('stderr') or cs.get('error'), language=None)
                            a, b = st.columns(2)
                            with a:
                                if cs.get('expected') is not None and (perm & 2):
                                    st.caption('✅ Expected')
                                    st.code(cs.get('expected'), language=None)
                                else:
                                    st.info('🔒 Expected')
                            with b:
                                if cs.get('actual') is not None and (perm & 4):
                                    st.caption('💻 Actual')
                                    st.code(cs.get('actual'), language=None)
                                else:
                                    st.info('🔒 Actual')

# 翻页
p1, p2, p3 = st.columns([2, 2, 8])
with p1:
    if st.button('⬅ 上一页', disabled=(st.session_state['sub_page'] <= 1),
                 use_container_width=True):
        st.session_state['sub_page'] = max(1, st.session_state['sub_page'] - 1)
        st.rerun()
with p2:
    if st.button('下一页 ➡', disabled=(not has_next),
                 type='primary' if has_next else 'secondary',
                 use_container_width=True):
        st.session_state['sub_page'] += 1
        st.rerun()
with p3:
    st.caption(f'当前页 #{st.session_state["sub_page"]}  ·  每页最多 {PAGE_SIZE} 条  ·  {"还有更多页" if has_next else "已是最后一页"}')

st.caption('© OJ 在线判题平台 · Streamlit 前端 + FastAPI 后端（Python 双栈架构）')
