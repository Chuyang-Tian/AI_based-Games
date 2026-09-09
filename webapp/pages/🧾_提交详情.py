# -*- coding: utf-8 -*-
"""提交详情页。"""

import os
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import (
    api,
    current_user,
    ensure_init,
    render_home_button,
    render_subheader,
    render_topbar,
    require_login_error,
)

st.set_page_config(page_title='提交详情 · OJ', page_icon='🧾', layout='wide', initial_sidebar_state='collapsed')

ensure_init()
render_topbar('独立提交详情页')

user = current_user()
if not user:
    require_login_error()
    st.stop()

raw_sid = st.query_params.get('id') or ''
sid = str(raw_sid[0] if isinstance(raw_sid, list) else raw_sid)

render_subheader([('🏠 判题首页', 'home'), ('📋 提交日志', 'submissions'), (f'🧾 提交 {sid or ""}', None)], 'submissions')

if not sid:
    st.warning('缺少提交 ID。')
    render_home_button()
    st.stop()

detail_code, detail_data, detail_err = api('GET', f'/api/submissions/{sid}')
detail = detail_data.get('data') if detail_code == 200 and isinstance(detail_data, dict) else None
log_code, log_data, log_err = api('GET', f'/api/submissions/{sid}/log')
log_detail = log_data.get('data') if log_code == 200 and isinstance(log_data, dict) else None

if not detail:
    st.error(f'详情加载失败：{detail_data.get("msg") if isinstance(detail_data, dict) else detail_err}')
    render_home_button()
    st.stop()

with st.container(border=True):
    c1, c2 = st.columns([7, 2])
    with c1:
        st.subheader(f"提交 #{detail.get('submission_id') or sid}", divider=False)
        st.caption(f"题目 ID: {detail.get('problem_id')}  |  用户 ID: {detail.get('user_id')}  |  语言: {detail.get('language')}")
    with c2:
        render_home_button()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric('状态', detail.get('status', '-'))
    m2.metric('得分', detail.get('score'))
    m3.metric('总分', detail.get('counts'))
    m4.metric('提交时间', detail.get('created_at') or detail.get('submit_time') or '-')

tabs = st.tabs(['基础信息', '编译与运行', '测试点详情'])

with tabs[0]:
    info = {
        'submission_id': detail.get('submission_id'),
        'problem_id': detail.get('problem_id'),
        'user_id': detail.get('user_id'),
        'status': detail.get('status'),
        'score': detail.get('score'),
        'counts': detail.get('counts'),
        'language': detail.get('language'),
    }
    st.json(info, expanded=True)

with tabs[1]:
    st.markdown('#### 编译信息')
    st.code((detail.get('compile_info') or {}).get('message') or '', language=None)
    st.markdown('#### 运行信息')
    st.code((detail.get('run_info') or {}).get('message') or '', language=None)
    if detail.get('error_info'):
        st.error(detail.get('error_info'))

with tabs[2]:
    details = (log_detail or {}).get('details') or []
    if details:
        table = []
        for item in details:
            table.append({
                '测试点': item.get('id'),
                '结果': item.get('result') or item.get('status'),
                '耗时': item.get('time') or item.get('time_ms'),
                '内存': item.get('memory') or item.get('memory_kb'),
            })
        st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)
    elif log_code == 403:
        st.info('当前用户无权查看测试点详情。')
    elif log_code != 200:
        st.error(f'日志加载失败：{log_data.get("msg") if isinstance(log_data, dict) else log_err}')
    else:
        st.info('该提交暂无测试点明细。')
