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
    get_locale,
    get_query_param,
    render_home_button,
    render_subheader,
    render_topbar,
    require_login_error,
    tr,
)

st.set_page_config(page_title='提交详情 · OJ', page_icon='🧾', layout='wide', initial_sidebar_state='collapsed')

ensure_init()
render_topbar(tr('page_submission_detail', '独立提交详情页'))


def t(zh: str, en: str) -> str:
    return en if get_locale() == 'en-US' else zh

user = current_user()
if not user:
    require_login_error()
    st.stop()

sid = get_query_param('id', 'submission_id', default='') or str(st.session_state.get('last_submission_id') or '')
if sid:
    st.session_state['last_submission_id'] = sid

render_subheader([(t('🏠 判题首页', '🏠 Home'), 'home'), (t('📋 提交日志', '📋 Submissions'), 'submissions'), (t(f'🧾 提交 {sid or ""}', f'🧾 Submission {sid or ""}'), None)], 'submissions')

if not sid:
    st.warning(t('缺少提交 ID。请从判题页重新提交，或从提交日志进入详情页。', 'Missing submission ID. Please resubmit from the judge page or open it from the submissions list.'))
    render_home_button()
    st.stop()

detail_code, detail_data, detail_err = api('GET', f'/api/submissions/{sid}')
detail = detail_data.get('data') if detail_code == 200 and isinstance(detail_data, dict) else None
log_code, log_data, log_err = api('GET', f'/api/submissions/{sid}/log')
log_detail = log_data.get('data') if log_code == 200 and isinstance(log_data, dict) else None

if not detail:
    st.error(t(f'详情加载失败：{detail_data.get("msg") if isinstance(detail_data, dict) else detail_err}', f'Failed to load submission detail: {detail_data.get("msg") if isinstance(detail_data, dict) else detail_err}'))
    render_home_button()
    st.stop()

with st.container(border=True):
    c1, c2 = st.columns([7, 2])
    with c1:
        st.subheader(t(f"提交 #{detail.get('submission_id') or sid}", f"Submission #{detail.get('submission_id') or sid}"), divider=False)
        st.caption(t(
            f"题目 ID: {detail.get('problem_id')}  |  用户 ID: {detail.get('user_id')}  |  语言: {detail.get('language')}",
            f"Problem ID: {detail.get('problem_id')}  |  User ID: {detail.get('user_id')}  |  Language: {detail.get('language')}"
        ))
    with c2:
        render_home_button()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(t('状态', 'Status'), detail.get('status', '-'))
    m2.metric(t('得分', 'Score'), detail.get('score'))
    m3.metric(t('总分', 'Total'), detail.get('counts'))
    m4.metric(t('提交时间', 'Submitted At'), detail.get('created_at') or detail.get('submit_time') or '-')

tabs = st.tabs([t('测试点详情', 'Testcase Details'), t('编译与运行', 'Compile & Run'), t('基础信息', 'Basic Info')])

with tabs[0]:
    details = (log_detail or {}).get('details') or []
    if details:
        table = []
        for item in details:
            table.append({
                t('测试点', 'Case'): item.get('id'),
                t('结果', 'Result'): item.get('result') or item.get('status'),
                t('耗时', 'Time'): item.get('time') or item.get('time_ms'),
                t('内存', 'Memory'): item.get('memory') or item.get('memory_kb'),
            })
        st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)
    elif log_code == 403:
        st.info(t('当前用户无权查看测试点详情。', 'You do not have permission to view testcase details.'))
    elif log_code != 200:
        st.error(t(f'日志加载失败：{log_data.get("msg") if isinstance(log_data, dict) else log_err}', f'Failed to load testcase log: {log_data.get("msg") if isinstance(log_data, dict) else log_err}'))
    else:
        st.info(t('该提交暂无测试点明细。', 'No testcase details for this submission yet.'))

with tabs[1]:
    st.markdown(f'#### {t("编译信息", "Compile Info")}')
    st.code((detail.get('compile_info') or {}).get('message') or '', language=None)
    st.markdown(f'#### {t("运行信息", "Run Info")}')
    st.code((detail.get('run_info') or {}).get('message') or '', language=None)
    if detail.get('status') == 'CE':
        st.info(tr('judge_status_hint', '可能是语言与代码不匹配。系统没有崩溃，你可以切换语言后重新提交。'))
    if detail.get('error_info'):
        if detail.get('status') == 'CE':
            st.warning(detail.get('error_info'))
        else:
            st.error(detail.get('error_info'))

with tabs[2]:
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
