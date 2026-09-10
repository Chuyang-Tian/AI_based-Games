"""
题目详情页——Step1 题目的"只读详情"视图 + 管理员编辑入口。
= URL 参数 =
  ?id=xxx           problem_id，必需。
= 功能 =
  - 未登录用户也能看题面/样例，点击"开始做题"会引导登录再跳判题；
  - 已登录用户：显示"我的最近提交"列表（当前 problem 的 submissions，按时间倒序），
                一键跳提交详情；
  - 管理员：额外显示"编辑题目 JSON 配置"表单 + "删除题目（二次确认）"按钮，
            修改后 PUT /api/problems/{pid}，并清掉 common 侧的 problem 列表缓存。
= Step1 对应点 =
  与 🗂题目管理 配合：增删改查的 "查（详情）/改/删" 都在这里完成。
  "加载" = GET /api/problems/{pid}，"校验" 由 app_fastapi PUT 路由里对 time_limit/memory_limit
  的数值合法校验完成。
"""
import json
import os
import sys
import streamlit as st
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import api, clear_problem_cache, current_user, ensure_init, get_locale, is_admin, page_url, render_page_link, render_home_button, render_sample_cases, render_rich_text, render_subheader, render_topbar, require_login_error, tr, toast_safe
st.set_page_config(page_title='题目详情 · OJ', page_icon='📄', layout='wide', initial_sidebar_state='collapsed')
ensure_init()
render_topbar(tr('page_problem_detail', '独立题目页'))

def t(zh: str, en: str) -> str:
    return en if get_locale() == 'en-US' else zh
user = current_user()
if not user:
    require_login_error()
    st.stop()
raw_pid = st.query_params.get('id') or ''
pid = str(raw_pid[0] if isinstance(raw_pid, list) else raw_pid)
if not pid:
    render_subheader([(t('🏠 判题首页', '🏠 Home'), 'home'), (t('📄 题目详情', '📄 Problem Detail'), None)], 'problems')
    st.warning(t('缺少题目 ID。', 'Missing problem ID.'))
    render_home_button()
    st.stop()
code, data, err = api('GET', f'/api/problems/{pid}')
problem = data.get('data') if code == 200 and isinstance(data, dict) else None
crumbs = [(t('🏠 判题首页', '🏠 Home'), 'home'), (t('🗂 题目管理', '🗂 Problem Admin') if is_admin() else t('📚 题库浏览', '📚 Problemset'), 'problems')]
crumbs.append((f'📄 {pid}', None))
render_subheader(crumbs, 'problems')
if not problem:
    st.error(t(f"题目加载失败：{(data.get('msg') if isinstance(data, dict) else err)}", f"Failed to load problem: {(data.get('msg') if isinstance(data, dict) else err)}"))
    render_home_button()
else:
    with st.container(border=True):
        top_left, top_mid, top_right = st.columns([6, 2, 2])
        with top_left:
            st.subheader(f"{problem.get('id')} · {problem.get('title')}")
            st.caption(t('难度', 'Difficulty') + f": {problem.get('difficulty') or '-'}  |  " + t('作者', 'Author') + f": {problem.get('author') or '-'}  |  " + t('来源', 'Source') + f": {problem.get('source') or '-'}")
        with top_mid:
            render_home_button()
        with top_right:
            render_page_link(t('进入判题页', 'Open Judge'), page_url('judge', id=problem.get('id')), primary=True)
        m1, m2, m3 = st.columns(3)
        m1.metric(t('时间限制', 'Time Limit'), f"{problem.get('time_limit') or '-'} s")
        m2.metric(t('内存限制', 'Memory Limit'), f"{problem.get('memory_limit') or '-'} MB")
        m3.metric(t('公开测试点', 'Public Details'), t('开启', 'On') if problem.get('public_cases') else t('关闭', 'Off'))
    tabs = st.tabs([t('题面详情', 'Statement'), t('题面样例', 'Statement Samples')] + ([t('管理配置', 'Settings')] if is_admin() else []))
    with tabs[0]:
        st.markdown(f"#### {t('题目描述', 'Description')}")
        render_rich_text(problem.get('description'), t('暂无描述', 'No description yet'))
        st.markdown(f"#### {t('输入描述', 'Input')}")
        render_rich_text(problem.get('input_description'), t('暂无输入描述', 'No input description yet'))
        st.markdown(f"#### {t('输出描述', 'Output')}")
        render_rich_text(problem.get('output_description'), t('暂无输出描述', 'No output description yet'))
        st.markdown(f"#### {t('数据范围与提示', 'Constraints & Notes')}")
        render_rich_text((problem.get('constraints') or '') + ('\n\n' + problem.get('hint') if problem.get('hint') else ''), t('暂无数据范围与提示', 'No constraints or notes yet'))
        if problem.get('tags'):
            st.caption(t('标签', 'Tags') + '：' + ', '.join(problem.get('tags') or []))
    with tabs[1]:
        render_sample_cases(problem.get('samples') or [], t('题面样例', 'Statement Samples'))
        if is_admin():
            st.divider()
            st.markdown(f"#### {t('（管理员）测试点数据', '(Admin Only) Testcase Payload')}")
            st.caption(t('以下为服务端用于判题的测试点数据，仅供管理员调试，具体构成与题面公开样例无对外明示关系。',
                         'The following payload is used by the server for judging and is admin-only. Its exact composition is not explicitly disclosed to end users.'))
            st.code(json.dumps(problem.get('testcases') or [], ensure_ascii=False, indent=2), language='json')
if is_admin() and problem:
    with tabs[2]:
        st.markdown(t('> 💡 这里直接控制「日志公开性」：当 **打开** 时，本人和其他已登录用户都能在提交详情里看到每个测试点的 AC/WA/TLE、耗时、内存（符合 TA-6 / TA-7 要求）；关闭时提交者本人仅能看到总分 score/counts，其他用户访问该日志返回 403。', '> 💡 Quick control for `public_cases`: when ON, both submitter & other logged-in users can see per-case status/time/memory in submission details; otherwise only total score/counts visible, others 403 (per TA-6/7).'))
        pc1, pc2 = st.columns([3, 2])
        with pc1:
            public_cases_now = bool(problem.get('public_cases', False))
            new_public_cases = st.checkbox(t('🔓 允许所有已登录用户查看该题所有提交的「测试点详情」（public_cases）', '🔓 Allow all logged-in users to view per-case details on this problem (`public_cases`)'), value=public_cases_now)
        with pc2:
            if st.button(t('立即应用日志公开性', 'Apply Log Visibility Now'), type='primary' if new_public_cases != public_cases_now else 'secondary', use_container_width=True):
                logv_code, logv_data, logv_err = api('PUT', f"/api/problems/{problem['id']}/log_visibility", {'public_cases': bool(new_public_cases)})
                if logv_code == 200:
                    clear_problem_cache()
                    toast_safe(t('public_cases 已更新，所有用户可见性立刻生效', 'Log visibility updated') + (t('（已开启）', '(ON)') if new_public_cases else t('（已关闭）', '(OFF)')), 'ok')
                    st.rerun()
                msg = ''
                if isinstance(logv_data, dict):
                    msg = logv_data.get('msg') or ''
                st.error(f'PUT log_visibility 失败 HTTP {logv_code}: {msg or logv_err}')
        with st.form('problem_detail_edit_form'):
            c1, c2, c3 = st.columns(3)
            with c1:
                title = st.text_input('标题', value=problem.get('title', ''))
            with c2:
                difficulty = st.selectbox('难度', ['简单', '中等', '困难'], index=['简单', '中等', '困难'].index(problem.get('difficulty', '中等')))
            with c3:
                author = st.text_input('作者', value=problem.get('author', ''))
            description = st.text_area('题目描述', value=problem.get('description', ''), height=140)
            input_description = st.text_area('输入描述', value=problem.get('input_description', ''), height=100)
            output_description = st.text_area('输出描述', value=problem.get('output_description', ''), height=100)
            constraints = st.text_area('数据范围', value=problem.get('constraints', ''), height=100)
            hint = st.text_area('提示', value=problem.get('hint', ''), height=80)
            c4, c5, c6 = st.columns(3)
            with c4:
                source = st.text_input('来源', value=problem.get('source', ''))
            with c5:
                time_limit = st.number_input('时间限制', min_value=0.1, step=0.1, value=float(problem.get('time_limit') or 1.0))
            with c6:
                memory_limit = st.number_input('内存限制', min_value=8, step=8, value=int(problem.get('memory_limit') or 128))
            tags = st.text_input('标签（逗号分隔）', value=', '.join(problem.get('tags') or []))
            samples_text = st.text_area('样例 JSON', value=json.dumps(problem.get('samples') or [], ensure_ascii=False, indent=2), height=160)
            testcases_text = st.text_area('测试点 JSON', value=json.dumps(problem.get('testcases') or [], ensure_ascii=False, indent=2), height=160)
            st.markdown(f"#### {t('结果可见性控制', 'Result Visibility Controls')}")
            visibility_options = [0, 1, 2]
            visibility_labels = {0: t('默认隐藏', 'Hidden by default'), 1: t('提交后可见', 'Visible after submission'), 2: t('始终可见', 'Always visible')}
            current_visibility = int(problem.get('test_case_visibility', 0) or 0)
            visibility_value = st.selectbox(t('测试点结果可见性', 'Testcase visibility'), visibility_options, index=visibility_options.index(current_visibility if current_visibility in visibility_options else 0), format_func=lambda value: visibility_labels[value])
            p1, p2 = st.columns(2)
            with p1:
                allow_see_input = st.checkbox(t('允许查看输入', 'Allow viewing input'), value=bool(problem.get('allow_see_input', False)))
                allow_see_actual = st.checkbox(t('允许查看实际输出', 'Allow viewing actual output'), value=bool(problem.get('allow_see_actual', False)))
            with p2:
                allow_see_expected = st.checkbox(t('允许查看期望输出', 'Allow viewing expected output'), value=bool(problem.get('allow_see_expected', False)))
                allow_see_error = st.checkbox(t('允许查看报错详情', 'Allow viewing error details'), value=bool(problem.get('allow_see_error', False)))
            save_col, delete_col = st.columns(2)
            save_clicked = save_col.form_submit_button('保存题目', type='primary', use_container_width=True)
            delete_clicked = delete_col.form_submit_button('删除题目', use_container_width=True)
        if save_clicked:
            try:
                samples = json.loads(samples_text)
                testcases = json.loads(testcases_text)
            except Exception as exc:
                st.error(f'JSON 解析失败：{exc}')
            else:
                payload = {'id': problem.get('id'), 'title': title.strip(), 'description': description, 'input_description': input_description, 'output_description': output_description, 'constraints': constraints, 'samples': samples, 'testcases': testcases, 'hint': hint, 'source': source.strip(), 'tags': [item.strip() for item in tags.split(',') if item.strip()], 'time_limit': float(time_limit), 'memory_limit': int(memory_limit), 'author': author.strip(), 'difficulty': difficulty}
                save_code, save_data, save_err = api('PUT', f"/api/problems/{problem['id']}", payload)
                if save_code == 200:
                    visibility_code, visibility_data, visibility_err = api('PUT', f"/api/problems/{problem['id']}/detailed_perms", {'public_cases': bool(visibility_value == 2), 'allow_see_input': bool(allow_see_input), 'allow_see_expected': bool(allow_see_expected), 'allow_see_actual': bool(allow_see_actual), 'allow_see_error': bool(allow_see_error), 'allow_user_config_runtime': bool(problem.get('allow_user_config_runtime', False)), 'allow_user_custom_debug_cases': bool(problem.get('allow_user_custom_debug_cases', False)), 'test_case_visibility': int(visibility_value)})
                    if visibility_code != 200:
                        st.error(f"{t('结果可见性更新失败', 'Visibility update failed')}：{(visibility_data.get('msg') if visibility_data else visibility_err)}")
                    clear_problem_cache()
                    toast_safe(t('题目已保存', 'Problem saved'), 'ok')
                    st.rerun()
                st.error(f"{t('保存失败', 'Save failed')}：{(save_data.get('msg') if save_data else save_err)}")
        if delete_clicked:
            delete_code, delete_data, delete_err = api('DELETE', f"/api/problems/{problem['id']}")
            if delete_code == 200:
                clear_problem_cache()
                toast_safe(t('题目已删除', 'Problem deleted'), 'ok')
                render_home_button()
                st.stop()
            st.error(f"{t('删除失败', 'Delete failed')}：{(delete_data.get('msg') if delete_data else delete_err)}")