# -*- coding: utf-8 -*-
"""
🤖 AI 智能命题（route_key=ai，登录用户均可进入，保存需 admin/teacher）
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
st.set_page_config(page_title='AI智能命题 - OJ', page_icon='🤖', layout='wide',
                   initial_sidebar_state='collapsed')

from common import (
    ensure_init, render_topbar, render_subheader,
    current_user, require_login_error, is_admin, is_teacher,
    api, toast_safe, goto, load_all_problems,
)

ensure_init()
render_topbar('AI 智能命题中心')
render_subheader([
    ('🏠 判题首页', 'home'),
    ('🤖 AI命题', None),
], 'ai')
user = current_user()

if not user:
    require_login_error()
    st.stop()

import pandas as pd

can_save = is_admin() or is_teacher()

c0, d0, _ = api('GET', '/api/ai/config')
if c0 != 200:
    c0, d0, _ = api('GET', '/api/ai/status')
ai_cfg_ok = False
if c0 == 200 and isinstance(d0, dict) and d0.get('data'):
    ai_data = d0['data']
    if ai_data.get('is_configured') or ai_data.get('api_key') or ai_data.get('provider'):
        ai_cfg_ok = True

if not ai_cfg_ok:
    with st.container(border=True):
        st.warning('⚠️ 您还未配置 AI 密钥（或密钥为空），请先前往【⚙️ AI 配置】填写 Provider 与 API Key。')
        if st.button('→ 前往 AI 配置', type='primary'):
            goto('ai_config')
            st.stop()

all_problems = load_all_problems()
all_tags = set()
for p in all_problems:
    for t in (p.get('tags') or []):
        if t:
            all_tags.add(str(t))
all_tags_list = sorted(list(all_tags))

DIFFICULTIES = ['简单', '中等', '困难']
LANGUAGES = ['python', 'cpp', 'java', 'js']
PROBLEM_TYPES = ['传统编程', '计算问答', '代码填空']

with st.container(border=True):
    st.subheader('🤖 AI 出题参数')
    with st.form('ai_generate_form'):
        a, b, c = st.columns(3)
        with a:
            ai_difficulty = st.selectbox('难度', DIFFICULTIES, index=1)
            ai_language = st.selectbox('编程语言', LANGUAGES, index=0)
        with b:
            ai_tags = st.multiselect('知识点 / 标签', all_tags_list if all_tags_list else ['数组','字符串','排序','递归','DP','贪心','树','图','数论'])
            ai_type = st.radio('题目类型', PROBLEM_TYPES, horizontal=True)
        with c:
            ai_count = st.number_input('出题数量', min_value=1, max_value=5, step=1, value=1)
        ai_extra = st.text_area('补充说明（可选，描述具体要求、数据范围、样例风格等）', height=100,
                                placeholder='例如：输入规模 n<=1e5，时间复杂度要求 O(nlogn)，至少包含 2 个边界样例')
        submitted = st.form_submit_button('🤖 调用 AI 生成', type='primary', use_container_width=True)

if submitted:
    payload = {
        'difficulty': ai_difficulty,
        'tags': list(ai_tags),
        'language': ai_language,
        'problem_type': ai_type,
        'count': int(ai_count),
        'additional_description': ai_extra or None,
    }
    gen_path = '/api/ai/generate'
    with st.spinner('🤖 正在让 AI 生成题目，请耐心等待…'):
        cg, dg, errg = api('POST', gen_path, payload)
    if cg != 200 or not (dg and dg.get('data')):
        cg2, dg2, errg2 = api('POST', '/api/ai/problems', payload)
        if cg2 == 200 and dg2 and dg2.get('data'):
            cg, dg, errg = cg2, dg2, errg2
    if cg == 200 and dg and dg.get('data'):
        st.session_state['ai_last_result'] = dg['data']
        toast_safe('✅ 生成成功！请查看下方结果', 'ok')
    else:
        c_probe, d_probe, _ = api('GET', '/api/ai/')
        if c_probe == 404:
            toast_safe('后端未启用 AI 引擎', 'warn')
        st.error(f'❌ 生成失败：{dg.get("msg") if dg else errg} (code={cg})')

st.subheader('🤖 生成结果预览')
last = st.session_state.get('ai_last_result')
if not last:
    st.info('（尚未生成题目。请先在上方填写参数并点击「🤖 调用 AI 生成」。）')
else:
    problems_out = last.get('problems') if isinstance(last, dict) and last.get('problems') else ([last] if isinstance(last, dict) else (last if isinstance(last, list) else []))

    if not problems_out:
        st.caption('（结果为空，请重新生成）')
    else:
        tab_labels = [f'📑 #{i+1} {(p.get("id") or "")} — {(p.get("title") or "未命名")}' for i, p in enumerate(problems_out)]
        result_tabs = st.tabs(tab_labels)
        for idx, p in enumerate(problems_out):
            with result_tabs[idx]:
                with st.expander('📖 题面 / 样例 / 测试用例详情', expanded=True):
                    col_meta1, col_meta2, col_meta3 = st.columns(3)
                    with col_meta1:
                        st.caption(f'**ID：** `{p.get("id") or "(未命名，请手动填写)"}`')
                        st.caption(f'**标题：** `{p.get("title") or ""}`')
                    with col_meta2:
                        st.caption(f'**难度：** `{p.get("difficulty") or ""}`')
                        st.caption(f'**标签：** `{(p.get("tags") or [])}`')
                    with col_meta3:
                        st.caption(f'**时间限制：** {p.get("time_limit") or 1.0}s')
                        st.caption(f'**内存限制：** {p.get("memory_limit") or 128}MB')

                    if p.get('description'):
                        st.subheader('📝 题目描述')
                        st.write(str(p['description']))
                    if p.get('input_description'):
                        st.subheader('📥 输入描述')
                        st.write(str(p['input_description']))
                    if p.get('output_description'):
                        st.subheader('📤 输出描述')
                        st.write(str(p['output_description']))
                    if p.get('constraints'):
                        st.subheader('⚠️ 约束 / 数据范围')
                        st.code(str(p['constraints']), language=None)
                    if p.get('hint'):
                        st.caption(f'💡 提示：{p["hint"]}')

                    samples = p.get('samples') or []
                    if samples:
                        st.subheader('📖 公开样例')
                        for si, s in enumerate(samples):
                            with st.container(border=True):
                                st.caption(f'样例 {si+1}')
                                sa, sb = st.columns(2)
                                with sa:
                                    st.caption('输入')
                                    st.code(s.get('input', ''), language=None)
                                with sb:
                                    st.caption('期望输出')
                                    st.code(s.get('output', ''), language=None)
                                if s.get('explanation'):
                                    st.caption(f'📝 解释：{s["explanation"]}')

                    tests = p.get('test_cases') or []
                    if tests:
                        st.subheader('🧪 正式测试点（隐藏）')
                        m_tc = st.container(border=True)
                        with m_tc:
                            st.caption(f'共 {len(tests)} 个正式测试点，将在保存后写入题目数据库。')
                            if st.checkbox(f'预览测试点内容（仅第 {min(3, len(tests))} 个）', key=f'preview_tc_{idx}'):
                                for ti in range(min(3, len(tests))):
                                    with st.container(border=True):
                                        st.caption(f'测试点 {ti+1}')
                                        ta, tb = st.columns(2)
                                        with ta:
                                            st.caption('输入')
                                            st.code(tests[ti].get('input', '')[:300], language=None)
                                        with tb:
                                            st.caption('输出')
                                            st.code(tests[ti].get('output', '')[:300], language=None)

                    std = p.get('standard_code') or p.get('std') or ''
                    if std:
                        st.subheader('🏆 标程（参考解）')
                        st.code(std, language=p.get('language', 'python'))

                b1, b2 = st.columns(2)
                with b1:
                    save_label = '💾 保存到题库（需管理员/老师）' if can_save else '🔒 保存到题库（权限不足）'
                    save_btn = st.button(save_label, key=f'ai_save_{idx}', type='primary',
                                        use_container_width=True, disabled=not can_save)
                    if save_btn and can_save:
                        payload_save = dict(p)
                        if not payload_save.get('id'):
                            payload_save['id'] = f'ai_{int(time.time()*1000)%100000:05d}'
                        if not payload_save.get('time_limit'):
                            payload_save['time_limit'] = 1.0
                        if not payload_save.get('memory_limit'):
                            payload_save['memory_limit'] = 128
                        if not payload_save.get('compare_mode'):
                            payload_save['compare_mode'] = 'exact'
                        payload_save.setdefault('author', user.get('username', 'ai'))
                        payload_save.setdefault('templates', {})
                        tpl = payload_save.get('template') or (payload_save.get('templates') or {}).get('python') or ''
                        payload_save['template'] = tpl
                        cs, ds, errs = api('POST', '/api/problems/', payload_save)
                        if cs in (200, 201) and ds and ds.get('data'):
                            saved_id = ds['data'].get('id')
                            toast_safe(f'✅ 已保存题目 {saved_id}', 'ok')
                            load_all_problems(force=True)
                            st.session_state[f'ai_saved_id_{idx}'] = saved_id
                        else:
                            st.error(f'保存失败：{ds.get("msg") if ds else errs} ({cs})')
                with b2:
                    sid_saved = st.session_state.get(f'ai_saved_id_{idx}') or p.get('id')
                    jump_disabled = not sid_saved
                    jump_btn = st.button('➜ 直接去判题', key=f'ai_jump_{idx}',
                                        use_container_width=True, disabled=jump_disabled)
                    if jump_btn and sid_saved:
                        goto('judge', id=str(sid_saved))

st.caption('© OJ 在线判题平台 · Streamlit 前端 + FastAPI 后端（Python 双栈架构）')
