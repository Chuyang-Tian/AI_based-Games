# -*- coding: utf-8 -*-
"""
OJ 判题首页（概览页）
"""
import os
import random
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import (
    current_user,
    ensure_init,
    load_all_problems,
    page_url,
    render_subheader,
    render_topbar,
    require_login_error,
    toast_safe,
)

st.set_page_config(page_title='OJ 调试平台 · 判题首页', page_icon='💻', layout='wide', initial_sidebar_state='collapsed')

ensure_init()
render_topbar('平台概览')
render_subheader([('🏠 判题首页', None)], 'home')

user = current_user()
if not user:
    require_login_error()
    st.caption('© OJ 在线判题平台 · Streamlit 前端 + FastAPI 后端（Python 双栈架构）')
    st.stop()

problems = load_all_problems()
easy_count = sum(1 for item in problems if item.get('difficulty') == '简单')
medium_count = sum(1 for item in problems if item.get('difficulty') == '中等')
hard_count = sum(1 for item in problems if item.get('difficulty') == '困难')
all_tags = sorted({tag for item in problems for tag in (item.get('tags') or [])})
random_problem = random.choice(problems) if problems else None
recent = problems[:6]

top_stats = st.columns(4)
top_stats[0].metric('题库总数', len(problems))
top_stats[1].metric('简单题', easy_count)
top_stats[2].metric('中等题', medium_count)
top_stats[3].metric('困难题', hard_count)

hero_left, hero_right = st.columns([2, 1], gap='large')

with hero_left:
    with st.container(border=True):
        st.subheader('开始使用', divider=False)
        st.caption('首页只保留概览与入口，题目浏览、提交记录、判题过程都放在独立页面里。')
        action_a, action_b, action_c = st.columns(3)
        with action_a:
            st.link_button('进入题库浏览', page_url('problems'), type='primary', use_container_width=True)
        with action_b:
            st.link_button('查看我的提交', page_url('submissions'), use_container_width=True)
        with action_c:
            if random_problem:
                st.link_button('随机挑一题', page_url('problem_detail', id=random_problem.get('id')), use_container_width=True)

    with st.container(border=True):
        st.subheader('快速入口', divider=False)
        quick_a, quick_b, quick_c = st.columns(3)
        with quick_a:
            st.markdown('**题库浏览**')
            st.caption('按题号、标题、难度、标签筛选，并进入独立题目页。')
            st.link_button('打开题库', page_url('problems'), use_container_width=True)
        with quick_b:
            st.markdown('**提交记录**')
            st.caption('查看个人提交目录，再进入独立提交详情页。')
            st.link_button('打开提交日志', page_url('submissions'), use_container_width=True)
        with quick_c:
            st.markdown('**AI 命题**')
            st.caption('查看 AI 配置、任务进度和生成结果。')
            st.link_button('打开 AI 页面', page_url('ai'), use_container_width=True)

with hero_right:
    with st.container(border=True):
        st.subheader('题库画像', divider=False)
        st.caption(f'当前共收录 {len(all_tags)} 个标签。')
        preview_tags = all_tags[:18]
        if preview_tags:
            pill_html = ''.join(f'<span class="oj-pill">{tag}</span>' for tag in preview_tags)
            st.markdown(pill_html, unsafe_allow_html=True)
        else:
            st.caption('暂无标签数据')

    with st.container(border=True):
        mini_left, mini_right = st.columns([3, 2])
        with mini_left:
            st.markdown('**刷新数据**')
            st.caption('仅在怀疑缓存未更新时使用。')
        with mini_right:
            st.caption('')
            if st.button('刷新题库', use_container_width=True):
                load_all_problems(force=True)
                toast_safe('题库缓存已刷新', 'ok')
                st.rerun()

with st.container(border=True):
    st.subheader('最近题目', divider=False)
    st.caption('展示少量样例题目，详细浏览请进入题库页。')
    if not recent:
        st.info('当前没有题目数据。')
    else:
        for item in recent:
            left, mid, right = st.columns([7, 2, 2])
            diff_cls = {
                '简单': 'oj-diff-easy',
                '中等': 'oj-diff-medium',
                '困难': 'oj-diff-hard',
            }.get(item.get('difficulty'), '')
            tags_html = ''.join(f'<span class="oj-pill">{tag}</span>' for tag in (item.get('tags') or [])[:4])
            with left:
                st.markdown(f"**{item.get('id')} · {item.get('title')}**")
                st.markdown(
                    f'<span class="oj-pill {diff_cls}">{item.get("difficulty") or "未标注"}</span>'
                    f'<span class="oj-pill">TL {item.get("time_limit") or "-" }s</span>'
                    f'<span class="oj-pill">ML {item.get("memory_limit") or "-" }MB</span>',
                    unsafe_allow_html=True,
                )
                if tags_html:
                    st.markdown(tags_html, unsafe_allow_html=True)
            with mid:
                st.link_button('题目详情', page_url('problem_detail', id=item.get('id')), use_container_width=True)
            with right:
                st.link_button('进入判题', page_url('judge', id=item.get('id')), type='primary', use_container_width=True)

st.caption('© OJ 在线判题平台 · Streamlit 前端 + FastAPI 后端（Python 双栈架构）')
