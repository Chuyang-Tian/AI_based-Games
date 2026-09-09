# -*- coding: utf-8 -*-
"""题目详情页。"""

import json
import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import (
    api,
    clear_problem_cache,
    current_user,
    ensure_init,
    get_locale,
    is_admin,
    page_url,
    render_page_link,
    render_home_button,
    render_sample_cases,
    render_rich_text,
    render_subheader,
    render_topbar,
    require_login_error,
    tr,
    toast_safe,
)

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
    st.error(t(f'题目加载失败：{data.get("msg") if isinstance(data, dict) else err}', f'Failed to load problem: {data.get("msg") if isinstance(data, dict) else err}'))
    render_home_button()
else:
    with st.container(border=True):
        top_left, top_mid, top_right = st.columns([6, 2, 2])
        with top_left:
            st.subheader(f"{problem.get('id')} · {problem.get('title')}", divider=False)
            st.caption(
                t('难度', 'Difficulty') + f": {problem.get('difficulty') or '-'}  |  " + t('作者', 'Author') + f": {problem.get('author') or '-'}  |  " + t('来源', 'Source') + f": {problem.get('source') or '-'}"
            )
        with top_mid:
            render_home_button()
        with top_right:
            render_page_link(t('进入判题页', 'Open Judge'), page_url('judge', id=problem.get('id')), primary=True)

        m1, m2, m3 = st.columns(3)
        m1.metric(t('时间限制', 'Time Limit'), f"{problem.get('time_limit') or '-'} s")
        m2.metric(t('内存限制', 'Memory Limit'), f"{problem.get('memory_limit') or '-'} MB")
        m3.metric(t('公开测试点', 'Public Details'), t('开启', 'On') if problem.get('public_cases') else t('关闭', 'Off'))

    tabs = st.tabs([t('题面详情', 'Statement'), t('样例与测试点', 'Samples & Cases')] + ([t('管理配置', 'Settings')] if is_admin() else []))

    with tabs[0]:
        st.markdown(f'#### {t("题目描述", "Description")}')
        render_rich_text(problem.get('description'), t('暂无描述', 'No description yet'))
        st.markdown(f'#### {t("输入描述", "Input")}')
        render_rich_text(problem.get('input_description'), t('暂无输入描述', 'No input description yet'))
        st.markdown(f'#### {t("输出描述", "Output")}')
        render_rich_text(problem.get('output_description'), t('暂无输出描述', 'No output description yet'))
        st.markdown(f'#### {t("数据范围与提示", "Constraints & Notes")}')
        render_rich_text((problem.get('constraints') or '') + ('\n\n' + problem.get('hint') if problem.get('hint') else ''), t('暂无数据范围与提示', 'No constraints or notes yet'))
        if problem.get('tags'):
            st.caption(t('标签', 'Tags') + '：' + ', '.join(problem.get('tags') or []))

    with tabs[1]:
        render_sample_cases(problem.get('samples') or [], t('公开样例', 'Public Samples'))
        if is_admin():
            st.markdown(f'#### {t("测试点数据", "Hidden Testcases")}')
            st.code(json.dumps(problem.get('testcases') or [], ensure_ascii=False, indent=2), language='json')

if is_admin() and problem:
    with tabs[2]:
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

            st.markdown(f'#### {t("结果可见性控制", "Result Visibility Controls")}')
            visibility_options = [0, 1, 2]
            visibility_labels = {
                0: t('默认隐藏', 'Hidden by default'),
                1: t('提交后可见', 'Visible after submission'),
                2: t('始终可见', 'Always visible'),
            }
            current_visibility = int(problem.get('test_case_visibility', 0) or 0)
            visibility_value = st.selectbox(
                t('测试点结果可见性', 'Testcase visibility'),
                visibility_options,
                index=visibility_options.index(current_visibility if current_visibility in visibility_options else 0),
                format_func=lambda value: visibility_labels[value],
            )
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
                payload = {
                    'id': problem.get('id'),
                    'title': title.strip(),
                    'description': description,
                    'input_description': input_description,
                    'output_description': output_description,
                    'constraints': constraints,
                    'samples': samples,
                    'testcases': testcases,
                    'hint': hint,
                    'source': source.strip(),
                    'tags': [item.strip() for item in tags.split(',') if item.strip()],
                    'time_limit': float(time_limit),
                    'memory_limit': int(memory_limit),
                    'author': author.strip(),
                    'difficulty': difficulty,
                }
                save_code, save_data, save_err = api('PUT', f"/api/problems/{problem['id']}", payload)
                if save_code == 200:
                    visibility_code, visibility_data, visibility_err = api(
                        'PUT',
                        f"/api/problems/{problem['id']}/detailed_perms",
                        {
                            'public_cases': bool(visibility_value == 2),
                            'allow_see_input': bool(allow_see_input),
                            'allow_see_expected': bool(allow_see_expected),
                            'allow_see_actual': bool(allow_see_actual),
                            'allow_see_error': bool(allow_see_error),
                            'allow_user_config_runtime': bool(problem.get('allow_user_config_runtime', False)),
                            'allow_user_custom_debug_cases': bool(problem.get('allow_user_custom_debug_cases', False)),
                            'test_case_visibility': int(visibility_value),
                        },
                    )
                    if visibility_code != 200:
                        st.error(f'{t("结果可见性更新失败", "Visibility update failed")}：{visibility_data.get("msg") if visibility_data else visibility_err}')
                    clear_problem_cache()
                    toast_safe(t('题目已保存', 'Problem saved'), 'ok')
                    st.rerun()
                st.error(f'{t("保存失败", "Save failed")}：{save_data.get("msg") if save_data else save_err}')

        if delete_clicked:
            delete_code, delete_data, delete_err = api('DELETE', f"/api/problems/{problem['id']}")
            if delete_code == 200:
                clear_problem_cache()
                toast_safe(t('题目已删除', 'Problem deleted'), 'ok')
                render_home_button()
                st.stop()
            st.error(f'{t("删除失败", "Delete failed")}：{delete_data.get("msg") if delete_data else delete_err}')
