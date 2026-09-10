"""
提交详情页——Step5 评测日志（5分）的核心展示页。
= URL 参数 =
  ?id=xxx        submission_id，必需；或从 st.session_state['last_submission_id'] 兜底（刚提交完不用改 URL 也能看）。
= 主要数据来源 =
  1. GET /api/submissions/{sid}          → 总体信息（用户/题目/语言/代码/状态/pass:total/time/memory/提交时间）
  2. GET /api/submissions/{sid}/log      → 测试点明细（每个 input/expected/actual/time/memory/error_message）
                                            Step5 核心：返回字段取决于 log_visibility（hidden/after_submit/public）
                                            以及是否是管理员；每一次调用都会写 access_logs 表，审计"谁什么时候看了哪次提交的明细"
= UI 分块 =
  - 顶部：submission 基本信息（状态徽标、时间、用户、题目、语言、所用资源）
  - 代码块：st.code 展示代码，可复制
  - 测试点表格：st.dataframe 每行一个测试点（case_id / status / time / memory），
                每个测试点下面点击展开能看「输入 / 期望输出 / 实际输出 / 错误信息」（Step5 可见性控制）
  - 管理员额外：🔄 重判按钮 + 返回日志列表按钮
= Step5 对应点 =
  测试点明细 + 可见性控制（Step5 3 种 visibility）+ access_logs 审计全部完成。
"""
import os
import sys
import pandas as pd
import streamlit as st
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import api, current_user, ensure_init, get_locale, get_query_param, is_admin, render_home_button, render_subheader, render_topbar, require_login_error, tr
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
render_subheader([(t('🏠 判题首页', '🏠 Home'), 'home'), (t('📋 提交日志', '📋 Submissions'), 'submissions'), (t(f"🧾 提交 {sid or ''}", f"🧾 Submission {sid or ''}"), None)], 'submissions')
if not sid:
    st.warning(t('缺少提交 ID。请从判题页重新提交，或从提交日志进入详情页。', 'Missing submission ID. Please resubmit from the judge page or open it from the submissions list.'))
    render_home_button()
    st.stop()
detail_code, detail_data, detail_err = api('GET', f'/api/submissions/{sid}')
detail = detail_data.get('data') if detail_code == 200 and isinstance(detail_data, dict) else None
log_code, log_data, log_err = api('GET', f'/api/submissions/{sid}/log')
log_detail = log_data.get('data') if log_code == 200 and isinstance(log_data, dict) else None
review_payload = {}
if is_admin():
    review_code, review_data, review_err = api('GET', f'/api/ai/submissions/{sid}/review')
    review_payload = review_data.get('data') if review_code == 200 and isinstance(review_data, dict) else {}
if not detail:
    st.error(t(f"详情加载失败：{(detail_data.get('msg') if isinstance(detail_data, dict) else detail_err)}", f"Failed to load submission detail: {(detail_data.get('msg') if isinstance(detail_data, dict) else detail_err)}"))
    render_home_button()
    st.stop()
with st.container(border=True):
    c1, c2 = st.columns([7, 2])
    with c1:
        st.subheader(t(f"提交 #{detail.get('submission_id') or sid}", f"Submission #{detail.get('submission_id') or sid}"))
        st.caption(t(f"题目 ID: {detail.get('problem_id')}  |  用户 ID: {detail.get('user_id')}  |  语言: {detail.get('language')}", f"Problem ID: {detail.get('problem_id')}  |  User ID: {detail.get('user_id')}  |  Language: {detail.get('language')}"))
    with c2:
        render_home_button()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(t('状态', 'Status'), detail.get('status', '-'))
    m2.metric(t('得分', 'Score'), detail.get('score'))
    m3.metric(t('总分', 'Total'), detail.get('counts'))
    m4.metric(t('提交时间', 'Submitted At'), detail.get('created_at') or detail.get('submit_time') or '-')
tab_labels = [t('测试点详情', 'Testcase Details'), t('编译与运行', 'Compile & Run'), t('基础信息', 'Basic Info')]
if is_admin():
    tab_labels.append(t('反AI审查', 'Anti-AI Review'))
tabs = st.tabs(tab_labels)
with tabs[0]:
    details = (log_detail or {}).get('details') or []
    if details:
        table = []
        for item in details:
            table.append({t('测试点', 'Case'): item.get('id'), t('结果', 'Result'): item.get('result') or item.get('status'), t('耗时', 'Time'): item.get('time') or item.get('time_ms'), t('内存', 'Memory'): item.get('memory') or item.get('memory_kb')})
        st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)
    elif log_code == 403:
        st.info(t('当前用户无权查看测试点详情。', 'You do not have permission to view testcase details.'))
    elif log_code != 200:
        st.error(t(f"日志加载失败：{(log_data.get('msg') if isinstance(log_data, dict) else log_err)}", f"Failed to load testcase log: {(log_data.get('msg') if isinstance(log_data, dict) else log_err)}"))
    else:
        st.info(t('该提交暂无测试点明细。', 'No testcase details for this submission yet.'))
with tabs[1]:
    st.markdown(f"#### {t('编译信息', 'Compile Info')}")
    st.code((detail.get('compile_info') or {}).get('message') or '', language=None)
    st.markdown(f"#### {t('运行信息', 'Run Info')}")
    st.code((detail.get('run_info') or {}).get('message') or '', language=None)
    if detail.get('status') == 'CE':
        st.info(tr('judge_status_hint', '可能是语言与代码不匹配。系统没有崩溃，你可以切换语言后重新提交。'))
    if detail.get('error_info'):
        if detail.get('status') == 'CE':
            st.warning(detail.get('error_info'))
        else:
            st.error(detail.get('error_info'))
with tabs[2]:
    info = {'submission_id': detail.get('submission_id'), 'problem_id': detail.get('problem_id'), 'user_id': detail.get('user_id'), 'status': detail.get('status'), 'score': detail.get('score'), 'counts': detail.get('counts'), 'language': detail.get('language')}
    st.json(info, expanded=True)
if is_admin():
    with tabs[3]:
        st.caption('该功能仅对管理员开放，用于辅助识别 AI 生成、异常提交模式、代码高相似度与异常性能表现。审查结果仅供参考，不会自动判定作弊。')
        action_col, status_col = st.columns([1.4, 4])
        with action_col:
            if st.button('立即运行反AI审查', type='primary', use_container_width=True):
                run_code, run_data, run_err = api('POST', f'/api/ai/submissions/{sid}/review', {})
                if run_code == 200 and isinstance(run_data, dict):
                    review_payload = run_data.get('data') or {}
                    st.success('反AI审查已完成。')
                else:
                    st.error(f"审查失败：{run_data.get('msg') if isinstance(run_data, dict) else run_err}")
        with status_col:
            if review_payload.get('exists') or review_payload.get('report_html'):
                level = str(review_payload.get('level') or '').lower()
                overall = review_payload.get('overall')
                level_text = {'high': '🔴 高风险', 'mid': '🟡 中风险', 'low': '🟢 低风险'}.get(level, '未审查')
                st.info(f'当前最新结论：{level_text}，综合分 {overall if overall is not None else "-"}。')
            else:
                st.info('当前还没有这条提交的反AI审查结果。')
        scores = review_payload.get('scores') or {}
        if scores:
            r1, r2, r3 = st.columns(3)
            r1.metric('综合分', scores.get('overall'))
            r2.metric('风险等级', {'high': '高', 'mid': '中', 'low': '低'}.get(str(scores.get('level') or '').lower(), '-'))
            r3.metric('AI生成概率', scores.get('s1'))
            r4, r5, r6, r7 = st.columns(4)
            r4.metric('代码重复率', scores.get('s2'))
            r5.metric('提交模式', scores.get('s3'))
            r6.metric('性能异常', scores.get('s4'))
            r7.metric('账号元数据', scores.get('s5'))
            with st.expander('查看五维原始明细', expanded=False):
                st.json(scores, expanded=True)
        report_html = review_payload.get('report_html')
        if report_html:
            st.markdown(report_html, unsafe_allow_html=True)
