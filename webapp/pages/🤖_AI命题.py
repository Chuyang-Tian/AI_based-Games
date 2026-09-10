"""
AI 智能命题页——Advance 进阶 10 分（AI 智能命题 R1~R4）的核心 UI。
= R1~R4 对应什么？
  R1 题目可读性    ：生成的题面是中文/英文自然语言，有背景、输入输出说明、数据范围；
  R2 样例正确性    ：至少给 2 组公开样例（input/output），在前端 normalize_problem_payload 里会自动挑出 public 样例；
  R3 隐藏测试点充分：生成若干隐藏测试点（基础/边界/卡常/极限各覆盖一些，STYLE_OPTIONS 可以选分布策略）；
  R4 功能易用性    ：用户可选"题目风格 / 难度 / 标签 / 测试点数量 / 模型 / 温度"，跑完可以直接"一键加入正式题库"。
= 数据流（答辩能画出来）=
  1. 用户填表 → 前端组织 prompt → POST /api/ai/generate（SSE 流式输出）；
  2. 后端 ai_engine.py：AIEngine 调 LLM /chat/completions 或走 Mock → 输出 SSE 事件
     start / step / draft / cases / token / complete → 前端逐行接收，显示"当前进度：正在生成题面/正在生成测试点..."；
  3. 完成后写 ai_drafts 表（草稿），前端展示 JSON 原始结果 + 渲染成题目卡 + 可编辑；
  4. 用户点"✅ 加入题库" → POST /api/ai/drafts/{id}/commit → 把草稿转成正式 problem 记录，
     之后 🗂题目管理 就能看到并让用户去做题。
= 容错 =
  - 没配置 API Key 也能跑：自动进入演示模式（不调用 AI，使用内置脚本/模板），返回固定 demo 题目 JSON，保证演示不卡；
  - LLM 返回格式不对（少了 description / test_cases 字段），后端 normalize_problem_payload 补默认值，不会炸 500。
"""
import os
import sys
import json
import time
import streamlit as st
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import api, clear_problem_cache, current_user, ensure_init, is_admin, render_rich_text, render_page_link, render_subheader, render_topbar, require_login_error, toast_safe
st.set_page_config(page_title='AI 命题 · OJ', page_icon='🤖', layout='wide', initial_sidebar_state='collapsed')
ensure_init()
render_topbar('AI 智能命题')
render_subheader([('🏠 判题首页', 'home'), ('🤖 AI 命题', None)], 'ai')
user = current_user()
if not user:
    require_login_error()
    st.stop()
STYLE_OPTIONS = {'plain': '裸题（直接给题）', 'story': '故事（常规背景）', 'fun': '趣味（轻松元素）', 'future': '科技（前沿包装）'}
SAMPLE_DISTRIBUTION_OPTIONS = {'balanced': '均衡（基础/边界/卡常各都有）', 'strict-optimal': '最优优先（更强调严格最优解）', 'edge-heavy': '边界优先（更强调极限与特殊情况）'}

def normalize_problem_payload(problem_json):
    difficulty_value = problem_json.get('difficulty', 5)
    if isinstance(difficulty_value, (int, float)):
        if difficulty_value <= 3:
            difficulty_text = '简单'
        elif difficulty_value <= 7:
            difficulty_text = '中等'
        else:
            difficulty_text = '困难'
    else:
        difficulty_text = str(difficulty_value or '中等')
    test_cases = problem_json.get('test_cases') or []
    samples = [{'input': item.get('input', ''), 'output': item.get('output', '')} for item in test_cases if item.get('visibility') == 'public']
    if not samples and test_cases:
        samples = [{'input': test_cases[0].get('input', ''), 'output': test_cases[0].get('output', '')}]
    payload = {'id': problem_json.get('problem_id_hint') or f'ai_{int(time.time())}', 'title': problem_json.get('title') or 'AI 生成题目', 'description': problem_json.get('description') or '', 'input_description': '详见题面中的输入格式部分。', 'output_description': '详见题面中的输出格式部分。', 'constraints': '详见题面中的数据范围部分。', 'samples': samples, 'testcases': [{'input': item.get('input', ''), 'output': item.get('output', '')} for item in test_cases], 'hint': '', 'source': 'AI 智能命题', 'tags': problem_json.get('tags') or [], 'time_limit': float(problem_json.get('time_limit') or 1.0), 'memory_limit': int(problem_json.get('memory_limit') or 128), 'author': user.get('username') or 'AI', 'difficulty': difficulty_text}
    return payload

def render_problem_preview(problem_json):
    tags = problem_json.get('tags') or []
    with st.container(border=True):
        st.subheader(problem_json.get('title') or 'AI 生成题目')
        if tags:
            st.caption(' / '.join((str(tag) for tag in tags)))
        if problem_json.get('description'):
            render_rich_text(problem_json.get('description'))
        cases = problem_json.get('test_cases') or []
        public_cases = [item for item in cases if item.get('visibility') == 'public']
        hidden_cases = [item for item in cases if item.get('visibility') != 'public']
        c1, c2, c3 = st.columns(3)
        c1.metric('公开样例', len(public_cases))
        c2.metric('隐藏样例', len(hidden_cases))
        c3.metric('总用例', len(cases))


def build_revision_task_payload(problem_json, feedback_text):
    difficulty_value = problem_json.get('difficulty', 5)
    if isinstance(difficulty_value, (int, float)):
        difficulty = int(max(1, min(10, difficulty_value)))
    else:
        text = str(difficulty_value or '')
        if '简' in text:
            difficulty = 3
        elif '难' in text:
            difficulty = 8
        else:
            difficulty = 5
    cases = problem_json.get('test_cases') or []
    return {
        'topic': problem_json.get('title') or 'AI 修订题目',
        'difficulty': difficulty,
        'style': 'plain',
        'sample_count': max(4, len(cases) or 4),
        'sample_distribution': 'balanced',
        'extra_tags': [str(tag) for tag in (problem_json.get('tags') or []) if str(tag).strip()],
        'source': 'AI 智能命题',
        'style_custom': '请尽量保留原题核心算法方向，仅根据修复点调整。',
        'requirement_notes': f'本次为基于已有草稿的修订任务。用户修复点：{feedback_text}',
        'revision_notes': feedback_text,
        'base_problem_json': problem_json,
    }
status_code, status_data, status_err = api('GET', '/api/ai/status')
ai_status = status_data.get('data') if isinstance(status_data, dict) and isinstance(status_data.get('data'), dict) else {}
allow_user_ai = bool(ai_status.get('allow_user_problem_create'))
ai_configured = bool(ai_status.get('configured'))
ai_mock_mode = bool(ai_status.get('mock_mode'))
if status_code != 200:
    st.warning('暂时无法读取 AI 配置状态，请稍后刷新页面重试。')
elif not is_admin() and (not allow_user_ai):
    st.info('当前管理员尚未开放普通用户使用 AI 命题功能。你可以先浏览其它页面，或联系管理员开启。')
    st.stop()
elif not ai_configured and (not ai_mock_mode):
    st.warning('当前尚未配置 AI 密钥。请联系管理员在“AI 配置”页面填写 DeepSeek 参数与密钥，或先让管理员启用「演示模式（不耗 Token）」。')
with st.container(border=True):
    st.subheader('创建命题任务')
    st.caption('题面风格已改为中文说明；括号里是简短解释，方便快速理解效果。')
    with st.form('ai_task_form'):
        c1, c2 = st.columns(2)
        with c1:
            topic = st.text_input('主题 / 知识点', placeholder='例如：二分答案、最短路、动态规划')
            difficulty = st.slider('难度（1-10）', min_value=1, max_value=10, value=5)
            sample_count = st.number_input('样例数量', min_value=4, max_value=20, value=10)
        with c2:
            style_label = st.selectbox('题面风格', options=list(STYLE_OPTIONS.keys()), index=0, format_func=lambda key: STYLE_OPTIONS[key])
            sample_distribution = st.selectbox('样例分布', options=list(SAMPLE_DISTRIBUTION_OPTIONS.keys()), index=0, format_func=lambda key: SAMPLE_DISTRIBUTION_OPTIONS[key])
            extra_tags = st.text_input('附加标签', placeholder='数组, 排序, 贪心')
        requirement = st.text_area('补充要求', height=90, placeholder='描述边界样例、输入规模、判题口味等')
        narrative = st.text_area('叙事 / 包装细节', height=90, placeholder='例如：校园、太空、机器人、未来科技、轻松趣味梗，但不要重复上面已经填过的内容')
        submit = st.form_submit_button('发起 AI 命题任务', type='primary', use_container_width=True)
    if submit:
        payload = {'topic': topic.strip() or requirement.strip() or '基础算法', 'difficulty': int(difficulty), 'style': style_label, 'sample_count': int(sample_count), 'sample_distribution': sample_distribution, 'extra_tags': [item.strip() for item in extra_tags.split(',') if item.strip()], 'source': 'AI 智能命题', 'style_custom': narrative.strip(), 'requirement_notes': requirement.strip()}
        task_code, task_data, task_err = api('POST', '/api/ai/problem-tasks/', payload, timeout=120)
        if task_code == 200 and isinstance(task_data, dict) and task_data.get('data'):
            st.session_state['ai_active_task_id'] = task_data['data'].get('task_id')
            st.session_state.pop('ai_latest_result', None)
            toast_safe('AI 任务已创建', 'ok')
            st.rerun()
        if task_code == 403:
            st.error('当前账号没有 AI 命题权限，请联系管理员开启“允许普通用户使用 AI 命题”。')
        else:
            st.error(f"任务创建失败：{(task_data.get('msg') if task_data else task_err)}")

def render_task_status():
    task_id = st.session_state.get('ai_active_task_id')
    if not task_id:
        st.info('当前没有进行中的 AI 任务。')
        return
    status_code, status_data, status_err = api('GET', f'/api/ai/problem-tasks/{task_id}')
    if status_code != 200 or not isinstance(status_data, dict) or (not status_data.get('data')):
        if status_code == 403:
            st.error('当前账号无权查看这个 AI 任务。')
        elif status_code == 404:
            st.warning('这个 AI 任务已经不存在，可能已被清理。')
        else:
            st.error(f"读取任务状态失败：{(status_data.get('msg') if status_data else status_err)}")
        return
    task = status_data['data']
    last_payload = task.get('last_payload') or {}
    status = task.get('status') or 'running'
    last_event = task.get('last_event') or ''
    event_label = {
        'start': '启动任务',
        'step': '执行阶段',
        'draft': '草稿已生成',
        'cases': '样例与测试点',
        'token': 'Token 统计',
        'retried': '自动重试',
        'complete': '生成完成',
        'error': '生成失败',
        'cancelled': '任务已取消',
    }.get(last_event, '等待中')
    cols = st.columns(4)
    cols[0].metric('任务 ID', task_id[:8])
    cols[1].metric('当前状态', status)
    cols[2].metric('当前阶段', event_label)
    cols[3].metric('完成时间', task.get('finished_at') or '-')
    event_text = {
        'start': '任务已创建，正在准备参数',
        'step': '正在执行当前阶段',
        'draft': '已经拿到题目草稿',
        'cases': '正在生成并校验样例',
        'token': '模型已返回一部分内容',
        'retried': '正在自动重试',
        'complete': '生成完成',
        'error': '生成失败',
        'cancelled': '任务已取消',
    }.get(last_event, '等待中')
    st.info(f'当前进度：{event_text}')
    if last_event == 'step':
        step_index = int(last_payload.get('index', 0) or 0)
        step_total = int(last_payload.get('total', 5) or 5)
        st.progress(min(step_index / max(step_total, 1), 1.0))
        step_title = str(last_payload.get('title') or f'阶段 {step_index}/{step_total}')
        step_text = str(last_payload.get('text') or '')
        st.caption(f"当前进行步骤：第 {step_index}/{step_total} 步 · {step_title}")
        if step_text:
            st.write(step_text)
    elif last_event == 'cases':
        st.success(str(last_payload.get('summary') or '样例脚本已运行完成'))
        st.caption(str(last_payload.get('script_stdout') or ''))
    elif last_event == 'token':
        st.caption(f"已消耗输入 {last_payload.get('input_tokens', 0)} tokens，输出 {last_payload.get('output_tokens', 0)} tokens。")
    elif last_event == 'retried':
        st.warning(f"自动重试中：{last_payload.get('reason', '')}")
    elif last_event == 'error':
        st.error(task.get('error_message') or last_payload.get('message') or '任务失败')
    if task.get('html_preview'):
        st.caption('当前草稿预览')
        st.markdown(task.get('html_preview'), unsafe_allow_html=True)
    if task.get('result'):
        has_new_result = st.session_state.get('ai_latest_result') != task.get('result')
        st.session_state['ai_latest_result'] = task.get('result')
        st.session_state.pop('ai_active_task_id', None)
        if has_new_result:
            st.rerun()
    elif status in ('error', 'cancelled'):
        st.session_state.pop('ai_active_task_id', None)
with st.container(border=True):
    st.subheader('任务进度')
    if hasattr(st, 'fragment'):

        @st.fragment(run_every='2s')
        def task_fragment():
            render_task_status()
        task_fragment()
    else:
        render_task_status()
        if st.button('刷新任务状态', use_container_width=True):
            st.rerun()
    active_task_id = st.session_state.get('ai_active_task_id')
    if active_task_id:
        if st.button('取消当前任务', use_container_width=True):
            cancel_code, cancel_data, cancel_err = api('POST', f'/api/ai/problem-tasks/{active_task_id}/cancel', {})
            if cancel_code == 200:
                toast_safe('任务已取消', 'warn')
                st.session_state.pop('ai_active_task_id', None)
                st.rerun()
            st.error(f"取消失败：{(cancel_data.get('msg') if cancel_data else cancel_err)}")
result = st.session_state.get('ai_latest_result')
active_task_id = st.session_state.get('ai_active_task_id')
if not result and active_task_id:
    fallback_code, fallback_data, fallback_err = api('GET', f'/api/ai/problem-tasks/{active_task_id}')
    fallback_task = fallback_data.get('data') if isinstance(fallback_data, dict) else {}
    if fallback_code == 200 and isinstance(fallback_task, dict) and fallback_task.get('result'):
        result = fallback_task.get('result')
        st.session_state['ai_latest_result'] = result
        st.session_state.pop('ai_active_task_id', None)
with st.container(border=True):
    st.subheader('生成结果')
    if not result:
        st.info('任务完成后会在这里展示题目 JSON，并可一键写入题库。')
    else:
        render_problem_preview(result)
        revision_info = result.get('_revision_feedback') or {}
        if revision_info.get('notes'):
            st.info(f"当前结果来自“按修复点再次提交”链路。最近一次修复点：{revision_info.get('notes')}")
        with st.container(border=True):
            st.markdown('#### 不满意当前题目？指出修复点后再次提交')
            st.caption('这里适合填写“背景太普通、样例规模偏小、数据范围不够卡、题面不够清楚”等明确修改意见。系统会基于当前草稿再次生成。')
            revision_feedback = st.text_area(
                '修复点 / 修改意见',
                value='',
                height=90,
                key='ai_revision_feedback',
                placeholder='例如：保留前缀和算法，但把背景改成图书馆预约；公开样例再丰富一点；隐藏测试点规模要更大，能卡掉 O(n^2) 解法。',
            )
            if st.button('🛠 根据修复点再次提交 AI 命题', use_container_width=True):
                feedback_text = revision_feedback.strip()
                if not feedback_text:
                    st.error('请先填写修复点，再发起再次提交。')
                else:
                    revision_payload = build_revision_task_payload(result, feedback_text)
                    task_code, task_data, task_err = api('POST', '/api/ai/problem-tasks/', revision_payload, timeout=120)
                    if task_code == 200 and isinstance(task_data, dict) and task_data.get('data'):
                        st.session_state['ai_active_task_id'] = task_data['data'].get('task_id')
                        st.session_state.pop('ai_latest_result', None)
                        st.session_state.pop('ai_active_draft_id', None)
                        toast_safe('已按修复点重新提交 AI 命题任务', 'ok')
                        st.rerun()
                    else:
                        st.error(f"再次提交失败：{(task_data.get('msg') if task_data else task_err)}")
        st.json(result, expanded=False)
        save_payload = normalize_problem_payload(result)
        case_gen_meta = result.get('_case_generation') or {}
        is_admin_view = bool(is_admin())
        tab_labels = ['Python 标程', 'C++ 标程', '测试点明细']
        if is_admin_view:
            tab_labels.append('样例脚本（管理员）')
        solution_tabs = st.tabs(tab_labels)
        with solution_tabs[0]:
            st.code(result.get('solution_python') or '# 暂无 Python 标程', language='python')
        with solution_tabs[1]:
            st.code(result.get('solution_cpp') or '// 暂无 C++ 标程', language='cpp')
        with solution_tabs[2]:
            all_cases = result.get('test_cases') or []
            st.caption(f'共 {len(all_cases)} 组测试点')
            for idx, case in enumerate(all_cases):
                vis = case.get('visibility') or 'hidden'
                with st.expander(f'Case #{idx} — {vis.upper()} · score={case.get("score",10)}', expanded=(idx < 2)):
                    c_in, c_out = st.columns(2)
                    c_in.text_area('Input', value=str(case.get('input') or ''), height=180, key=f'case_in_{idx}')
                    c_out.text_area('Output', value=str(case.get('output') or ''), height=180, key=f'case_out_{idx}')
        if is_admin_view and len(solution_tabs) >= 4:
            with solution_tabs[3]:
                st.info(
                    '「样例脚本」是本次 AI 生成测试用例时用到的原始造数程序（generate_test.py）。'
                    ' 管理员可以：① 修改后保存回草稿；② 调整额外用例数 + 种子；③ 运行脚本追加/替换隐藏用例。'
                )
                default_script = str(case_gen_meta.get('script_source') or '')
                if not default_script.strip():
                    default_script = '"""\n未提供原始脚本。你可以在这里按约定编写 generate_test.py：\n' \
                                     '运行后同目录应产生 case_000.in, case_001.in, ...\n' \
                                     '脚本顶部可声明：N_CASES = 8； random.seed(...) 便于复现。\n"""\nimport os, random\nrandom.seed(42)\nN_CASES = 8\nBASE_DIR = os.path.dirname(os.path.abspath(__file__))\n\nfor i in range(N_CASES):\n    n = random.randint(1, 20)\n    arr = [random.randint(-10**6, 10**6) for _ in range(n)]\n    with open(os.path.join(BASE_DIR, f"case_{i:03d}.in"), "w", encoding="utf-8") as f:\n        f.write(str(n) + "\\n")\n        f.write(" ".join(map(str, arr)) + "\\n")\n    print(f"CASE{i}: N={n}")\nprint("OK")\n'
                edited_script = st.text_area(
                    'generate_test.py（样例脚本原始代码）',
                    value=default_script,
                    height=340,
                    key='ai_case_script_editor',
                )
                st.caption('脚本语言：Python（Streamlit 当前文本框不支持代码高亮编辑）')
                stdout_prev = str(case_gen_meta.get('script_stdout') or '')
                st.text_area('上次运行 stdout / stderr 日志', value=stdout_prev or '（暂无日志）',
                             height=140, key='ai_case_script_stdout_prev')
                run_c1, run_c2, run_c3, run_c4 = st.columns([1, 1, 1.5, 1.5])
                extra_n = run_c1.number_input('额外新增组数', min_value=0, max_value=80, value=0,
                                              help='修改脚本中 N_CASES = 原值 + 额外新增，再运行')
                seed_delta = run_c2.number_input('种子偏移', min_value=0, max_value=10000, value=0,
                                                 help='用于在不修改源代码的前提下换一批随机数据')
                merge_opt = run_c3.selectbox('写回策略', options=['append_hidden', 'replace_hidden', 'replace_all'],
                                            format_func=lambda k: {
                                                'append_hidden': '仅追加到隐藏用例（保留现有）',
                                                'replace_hidden': '保留公开样例，替换所有隐藏',
                                                'replace_all': '完全替换（前2个强制公开，其余隐藏）',
                                            }.get(k, k))
                persist_opt = run_c4.checkbox('运行后自动回写草稿', value=True)
                btn_c1, btn_c2 = st.columns(2)
                with btn_c1:
                    if st.button('💾 保存脚本到草稿', use_container_width=True):
                        merged_meta = dict(case_gen_meta)
                        merged_meta['script_source'] = edited_script
                        edited_result = dict(result)
                        edited_result['_case_generation'] = merged_meta
                        draft_id = st.session_state.get('ai_active_draft_id')
                        if draft_id:
                            puc, pud, pue = api('PUT', f'/api/ai/drafts/{draft_id}',
                                               {'problem_json': edited_result}, timeout=60)
                            if puc == 200:
                                st.session_state['ai_latest_result'] = edited_result
                                result = edited_result
                                toast_safe('脚本已保存到草稿', 'ok')
                                st.rerun()
                            else:
                                st.error(f"保存失败：{(pud.get('msg') if pud else pue)}")
                        else:
                            st.session_state['ai_latest_result'] = edited_result
                            result = edited_result
                            toast_safe('脚本已在本页面临时保存；记得随后“保存到题库”或先保存草稿', 'warn')
                            st.rerun()
                with btn_c2:
                    if st.button('▶ 运行脚本并按策略写回', type='primary', use_container_width=True):
                        draft_id = st.session_state.get('ai_active_draft_id')
                        if draft_id and persist_opt:
                            run_payload = {'extra_cases': int(extra_n), 'seed_offset': int(seed_delta),
                                           'merge_mode': merge_opt, 'persist': True}
                            rc, rd, re_ = api('POST', f'/api/ai/drafts/{draft_id}/run-script', run_payload, timeout=120)
                            if rc in (200, 422):
                                data = rd.get('data') if isinstance(rd, dict) else {}
                                if rc == 200:
                                    if persist_opt and data.get('persisted'):
                                        toast_safe(data.get('summary') or '运行成功，已回写草稿', 'ok')
                                    else:
                                        toast_safe(data.get('summary') or '运行成功', 'ok')
                                    gc, gd, _ = api('GET', f'/api/ai/drafts')
                                    row = None
                                    if gc == 200 and isinstance(gd, dict) and isinstance(gd.get('data'), dict):
                                        for r in gd['data'].get('list') or []:
                                            if str(r.get('id')) == str(draft_id):
                                                row = r; break
                                    if row:
                                        try:
                                            updated_json = json.loads(row['problem_json']) if isinstance(row.get('problem_json'), str) else (row.get('problem_json') or {})
                                            st.session_state['ai_latest_result'] = updated_json
                                            result = updated_json
                                            st.rerun()
                                        except Exception:
                                            pass
                                    st.success(data.get('summary') or '运行完成')
                                else:
                                    st.error(f"脚本执行失败：{rd.get('msg') if rd else re_}；详细：{data.get('script_stderr') or data.get('script_stdout') or ''}")
                            else:
                                st.error(f"调用失败：{rd.get('msg') if rd else re_}")
                        else:
                            toast_safe('当前结果尚未保存为草稿，无法在服务端运行；请先点“保存脚本到草稿”或使用保存草稿按钮。将走前端轻量校验仅更新本页 result。', 'warn')
                            if not draft_id:
                                sv_code, sv_data, sv_err = api('POST', '/api/ai/drafts', {'problem_json': result}, timeout=60)
                                if sv_code == 200 and isinstance(sv_data, dict) and sv_data.get('data'):
                                    st.session_state['ai_active_draft_id'] = sv_data['data'].get('id')
                                    toast_safe(f"已自动创建草稿 #{sv_data['data'].get('id')}，请再次点击“运行脚本”", 'ok')
                                    st.rerun()
        extra_row1, extra_row2 = st.columns([2, 1])
        with extra_row1:
            if st.button('💾 另存到草稿箱（用于后续“运行样例脚本”）', use_container_width=True):
                sv1, sv2, sv3 = api('POST', '/api/ai/drafts', {'problem_json': result}, timeout=60)
                if sv1 == 200 and isinstance(sv2, dict) and sv2.get('data'):
                    st.session_state['ai_active_draft_id'] = sv2['data'].get('id')
                    toast_safe(f"已存草稿 #{sv2['data'].get('id')}，现在可以在样例脚本 Tab 中运行脚本生成更多用例", 'ok')
                    st.rerun()
                else:
                    st.error(f"草稿保存失败：{(sv2.get('msg') if sv2 else sv3)}")
        with extra_row2:
            draft_id_current = st.session_state.get('ai_active_draft_id')
            st.caption(f'关联草稿 ID：`{draft_id_current if draft_id_current else "（未关联）"}`')
        save_col, judge_col = st.columns(2)
        with save_col:
            if st.button('保存到题库', type='primary', use_container_width=True):
                save_code, save_data, save_err = api('POST', '/api/problems/', save_payload)
                if save_code == 200:
                    clear_problem_cache()
                    st.session_state['ai_saved_problem_id'] = save_payload['id']
                    toast_safe('题目已写入题库', 'ok')
                    st.rerun()
                elif save_code == 403:
                    st.error('当前账号没有保存到题库的权限。')
                else:
                    st.error(f"保存失败：{(save_data.get('msg') if save_data else save_err)}")
        with judge_col:
            saved_problem_id = st.session_state.get('ai_saved_problem_id') or save_payload['id']
            render_page_link('打开题目管理页', '/%E9%A2%98%E7%9B%AE%E7%AE%A1%E7%90%86')
            st.caption(f'目标题目 ID：`{saved_problem_id}`')

with st.container(border=True):
    st.subheader('草稿箱（加载已有草稿可继续运行 / 再生成样例）')
    drafts_code, drafts_data, drafts_err = api('GET', '/api/ai/drafts')
    if drafts_code != 200 or not isinstance(drafts_data, dict) or not isinstance(drafts_data.get('data'), dict):
        st.warning(f'无法读取草稿列表：{(drafts_data.get("msg") if drafts_data else drafts_err)}')
    else:
        rows = (drafts_data['data'].get('list') or [])
        if not rows:
            st.info('当前暂无草稿。上面完成一次 AI 命题后，点击“另存到草稿箱”即可出现在这里。')
        else:
            rows_sorted = sorted(list(rows), key=lambda r: int(r.get('updated_at') or 0), reverse=True)
            for row in rows_sorted[:20]:
                try:
                    json_val = row.get('problem_json')
                    if isinstance(json_val, str):
                        pj = json.loads(json_val)
                    else:
                        pj = json_val or {}
                except Exception:
                    pj = {}
                title = pj.get('title') or '（无标题）'
                tags = ' / '.join(str(x) for x in (pj.get('tags') or []))
                case_cnt = len(pj.get('test_cases') or [])
                cg = pj.get('_case_generation') or {}
                has_script = '✅ 有脚本' if (cg.get('script_source') or '').strip() else '⚠️ 无脚本'
                c1, c2, c3, c4, c5 = st.columns([3, 2, 1.2, 1.4, 1.8])
                c1.markdown(f"**草稿 #{row.get('id')}**: {title}")
                c2.caption(tags[:40] or '（无标签）')
                c3.metric('用例', case_cnt)
                c4.caption(has_script)
                with c5:
                    if st.button(f'加载此草稿', key=f'load_draft_{row.get("id")}', use_container_width=True):
                        st.session_state['ai_latest_result'] = pj
                        st.session_state['ai_active_draft_id'] = row.get('id')
                        st.session_state.pop('ai_active_task_id', None)
                        toast_safe(f'已加载草稿 #{row.get("id")}', 'ok')
                        st.rerun()
                    if is_admin() and st.button(f'删除', key=f'del_draft_{row.get("id")}', use_container_width=True):
                        dc, dd, de = api('DELETE', f'/api/ai/drafts/{row.get("id")}')
                        if dc == 200:
                            toast_safe('已删除', 'warn')
                            st.rerun()
                        else:
                            st.error(f"删除失败：{(dd.get('msg') if dd else de)}")
