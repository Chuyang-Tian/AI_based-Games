# -*- coding: utf-8 -*-
"""
OJ 判题首页（Streamlit 原生组件版）
"""
import sys, os, random
from urllib.parse import quote as _quote
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import streamlit as st
from common import (
    ensure_init, render_topbar, render_subheader,
    current_user, require_login_error,
    load_all_problems, get_filtered_problems, toast_safe, goto,
)

st.set_page_config(page_title='OJ 调试平台 · 判题首页', page_icon='💻',
                   layout='wide', initial_sidebar_state='collapsed')

ensure_init()
render_topbar('Python 判题引擎')
render_subheader([('🏠 判题首页', None)], 'home')

user = current_user()
if not user:
    require_login_error()
    st.caption('© OJ 在线判题平台 · Streamlit 前端 + FastAPI 后端（Python 双栈架构）')
    st.stop()

problems = load_all_problems()
if 'home_diff' not in st.session_state:
    st.session_state['home_diff'] = ''
if 'home_tags' not in st.session_state:
    st.session_state['home_tags'] = []

# 主体两列（左筛选 / 右题目卡片列表）
col_left, col_right = st.columns([1, 3], gap='large')

with col_left:
    filter_box = st.container(border=True)
    with filter_box:
        st.markdown('**🔍 搜索题目**')
        kw = st.text_input('搜索输入框', label_visibility='collapsed',
                           placeholder='按 ID 或标题搜索...', key='home_search')

        st.markdown('**🎯 难度筛选**')
        d1, d2, d3, d4 = st.columns(4)
        diff_buttons = [('', '全部'), ('简单', '简单'), ('中等', '中等'), ('困难', '困难')]
        for i, (val, label) in enumerate(diff_buttons):
            active = (st.session_state['home_diff'] == val)
            with [d1, d2, d3, d4][i]:
                if st.button(label, use_container_width=True, type='primary' if active else 'secondary',
                             key=f'home_diff_{val or "all"}'):
                    st.session_state['home_diff'] = val
                    st.rerun()

        st.markdown('**🏷️ 标签筛选**')
        all_tags = sorted({t for p in problems for t in (p.get('tags') or [])})
        if all_tags:
            sel_tags = st.multiselect('已选标签（多选）', all_tags, default=st.session_state['home_tags'],
                                      label_visibility='collapsed', key='home_tags_ms')
            st.session_state['home_tags'] = sel_tags or []
        else:
            st.caption('（暂无标签）')

        st.divider()
        st.metric('📚 题库总数', f'{len(problems)} 道')

        b1, b2 = st.columns(2)
        with b1:
            if st.button('🔄 刷新题库', use_container_width=True, key='home_refresh'):
                load_all_problems(force=True)
                toast_safe('题库已刷新', 'ok')
                st.rerun()
        with b2:
            if st.button('⚡ 随机选题', use_container_width=True, key='home_random') and problems:
                pick = random.choice(problems)
                goto('judge', id=pick['id'])

with col_right:
    # 顶部四宫格统计
    m1, m2, m3, m4 = st.columns(4)
    m1.metric('📚 题库总数', f'{len(problems)} 道')
    m2.metric('🟢 简单', f'{sum(1 for p in problems if p.get("difficulty") == "简单")} 道')
    m3.metric('🟡 中等', f'{sum(1 for p in problems if p.get("difficulty") == "中等")} 道')
    m4.metric('🔴 困难', f'{sum(1 for p in problems if p.get("difficulty") == "困难")} 道')

    # 应用筛选
    sel_tags = set(st.session_state.get('home_tags') or [])
    filtered = get_filtered_problems(problems, st.session_state.get('home_search', ''),
                                     st.session_state.get('home_diff', ''), list(sel_tags))
    st.caption(f'当前筛选后共 **{len(filtered)}** 道题目。点击右侧「➜ 判题」进入独立判题页（URL 独立，可刷新/后退）。')

    if not filtered:
        st.info('（没有匹配的题目，请调整搜索或筛选条件）')
    else:
        for p in filtered:
            card = st.container(border=True)
            with card:
                pid = p.get('id') or ''
                title = p.get('title') or ''
                diff = p.get('difficulty') or ''
                author = p.get('author') or 'system'
                tags = p.get('tags') or []
                tl = p.get('time_limit') or '?'
                ml = p.get('memory_limit') or '?'
                desc_summary = (p.get('description') or '')[:80]
                top1, top2, top3 = st.columns([7, 1, 1])
                judge_url = '/判题器?id=' + _quote(str(pid))
                with top1:
                    st.subheader(f'{pid}  ·  {title}', divider=False)
                    cap = f'难度: {diff or "-"}  |  作者: {author}  |  TL: {tl}s  |  ML: {ml}MB'
                    if tags:
                        cap += f'  |  标签: {", ".join(tags)}'
                    st.caption(cap)
                    st.caption(desc_summary + (' …' if len(desc_summary) >= 80 else ''))
                with top2:
                    st.caption(' ')
                    st.link_button('详情', judge_url, use_container_width=True,
                                   key=f'detail_btn_{pid}')
                with top3:
                    st.caption(' ')
                    st.link_button('➜ 判题', judge_url, type='primary',
                                   use_container_width=True,
                                   key=f'go_judge_{pid}')

st.caption('© OJ 在线判题平台 · Streamlit 前端 + FastAPI 后端（Python 双栈架构）')
