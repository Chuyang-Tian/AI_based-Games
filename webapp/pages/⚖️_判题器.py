# -*- coding: utf-8 -*-
"""
判题器（Streamlit 原生组件版，URL 通过 ?id=xxx 传递题目 ID，支持刷新保持）
"""
import sys, os, time, difflib, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st

st.set_page_config(page_title='判题器 · OJ', page_icon='⚖️', layout='wide',
                   initial_sidebar_state='collapsed')

from common import (
    ensure_init, render_topbar, render_subheader,
    current_user, require_login_error, is_admin,
    load_all_problems, load_languages, api, toast_safe, goto,
)

LANG_DEFAULT_CODE = {
    'python': '# 在这里写 Python 3 代码\n# 请从标准输入读取，输出到标准输出\nimport sys\n\nfor line in sys.stdin:\n    line = line.strip()\n    if not line:\n        continue\n    a, b = map(int, line.split())\n    print(a + b)\n',
    'cpp': '// C++17\n#include <bits/stdc++.h>\nusing namespace std;\nint main(){\n    ios::sync_with_stdio(false);\n    long long a,b;\n    while(cin>>a>>b) cout<<a+b<<"\\n";\n    return 0;\n}\n',
    'java': 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        while (sc.hasNext()) {\n            long a = sc.nextLong(), b = sc.nextLong();\n            System.out.println(a + b);\n        }\n    }\n}\n',
    'js': '// Node.js 20\nconst readline = require("readline");\nconst rl = readline.createInterface({input: process.stdin});\nrl.on("line", line => {\n    const [a,b] = line.trim().split(/\\s+/).map(Number);\n    console.log(a+b);\n});\n',
}

ensure_init()
user = current_user()
render_topbar('独立判题页')

raw_pid = st.query_params.get('id') or ''
if isinstance(raw_pid, (list, tuple)):
    pid = str(raw_pid[0]) if raw_pid else ''
else:
    pid = str(raw_pid)
if not pid:
    st.info('⚠️ 没有指定题目 ID（URL 需包含 ?id=xxx）。')
    if st.button('← 返回首页', type='primary'):
        goto('home')
    st.stop()

problems = load_all_problems()
problem = next((p for p in problems if str(p.get('id', '')) == str(pid)), None)
if not problem:
    c, d, _ = api('GET', f'/api/problems/{pid}')
    if c == 200 and d and d.get('data'):
        problem = d['data']

bc = [('🏠 判题首页', 'home'),
      ('🗂 题目管理' if is_admin() else '📚 题库', 'problems')]
if problem:
    bc.append((f'📝 {problem.get("id")} · {problem.get("title")}', None))
    render_subheader(bc, 'problems')
else:
    render_subheader(bc + [('题目不存在', None)], 'problems')

if not user:
    require_login_error()
    st.stop()

if not problem:
    st.error(f'❌ 题目 `{pid}` 不存在。')
    if st.button('← 返回首页', type='primary'):
        goto('home')
    st.stop()
problem = problem or {}

# 预加载语言列表
@st.cache_data(show_spinner=False, ttl=300)
def get_langs():
    return [{'name': name} for name in load_languages()]

langs = get_langs()
lang_names = [l['name'] for l in langs]
if 'python' not in lang_names:
    lang_names = ['python'] + lang_names

# 判题页本地状态
ss = st.session_state
pk = f'judge_{pid}_'
def gs(k, d=None):
    return ss.get(pk + k, d)
def ss_set(k, v):
    ss[pk + k] = v

if problem and not gs('inited'):
    ss_set('inited', True)
    lang = problem.get('language') or (lang_names[0] if lang_names else 'python')
    if lang not in lang_names and lang_names:
        lang = lang_names[0]
    ss_set('lang', lang)
    tpl = problem.get('template') or (
        isinstance(problem.get('templates'), dict) and problem['templates'].get(lang, '')) \
        or LANG_DEFAULT_CODE.get(lang, '')
    ss_set('code', tpl)
    ss_set('tl', float(problem.get('time_limit') or 1.0))
    ss_set('ml', int(problem.get('memory_limit') or 128))
    ss_set('cm', problem.get('compare_mode') or 'exact')
    ss_set('samples', True)
    ss_set('custom', True)
    ss_set('only_custom', False)
    ss_set('custom_list', [])
    ss_set('last', None)

# ============ 题面卡片（st.container border=True）============
p_title = problem.get('title') or ''
p_id = problem.get('id') or ''
p_diff = problem.get('difficulty') or ''
p_tags = problem.get('tags') or []
p_author = problem.get('author') or 'system'
p_source = problem.get('source') or 'N/A'
p_tl = problem.get('time_limit') or '?'
p_ml = problem.get('memory_limit') or '?'

header_card = st.container(border=True)
with header_card:
    t1, t2 = st.columns([8, 2])
    with t1:
        st.subheader(f'📖  {p_id}  ·  {p_title}', divider=False)
        tagstr = f'难度: {p_diff or "-"}  |  作者: {p_author}  |  来源: {p_source}'
        if p_tags:
            tagstr += f'  |  标签: {", ".join(p_tags)}'
        st.caption(tagstr)
    with t2:
        st.caption('')
        st.caption('')
        if st.button('← 返回题库', use_container_width=True,
                     on_click=goto, kwargs={'route_key': 'problems'}):
            pass

    m1, m2, m3 = st.columns(3)
    m1.metric('⏱ 时间限制', f'{p_tl} s')
    m2.metric('💾 内存限制', f'{p_ml} MB')
    m3.metric('🧑‍🏫 出题 / 来源', f'{p_author} / {p_source}')

    if problem.get('description'):
        st.markdown('#### 📝 题目描述')
        st.info(problem['description'])
    if problem.get('input_description'):
        st.markdown('#### 📥 输入描述')
        st.info(problem['input_description'])
    if problem.get('output_description'):
        st.markdown('#### 🎯 输出描述')
        st.info(problem['output_description'])
    if problem.get('constraints') or problem.get('hint'):
        extra = (problem.get('constraints') or '')
        if problem.get('hint'):
            extra += ('\n\n💡 ' + problem['hint'])
        if extra.strip():
            st.markdown('#### ⚙️ 数据范围与提示')
            st.warning(extra)

# ============ 下方主网格两列 ============
col_left, col_right = st.columns(2, gap='large')

# 左列：代码编辑卡
with col_left:
    code_card = st.container(border=True)
    with code_card:
        st.subheader('💻 代码编辑', divider=False)
        c0, c1, c2 = st.columns([3, 3, 2])
        with c0:
            cur_lang = gs('lang')
            if cur_lang not in lang_names and lang_names:
                cur_lang = lang_names[0]
            new_lang = st.selectbox('语言', lang_names, index=lang_names.index(cur_lang),
                                    key=pk + 'w_lang')
            if new_lang != cur_lang:
                ss_set('lang', new_lang)
                cur_tpl = (problem.get('template') or
                          (isinstance(problem.get('templates'), dict) and problem['templates'].get(new_lang, ''))
                          or LANG_DEFAULT_CODE.get(new_lang, ''))
                ss_set('code', cur_tpl)
                st.rerun()
        with c1:
            st.caption('')
            cm_opts = ['exact', 'trim', 'numeric']
            cm_labels = {'exact':'精确(行对比)', 'trim':'Trim 去首尾空格', 'numeric':'数值容差'}
            cur_cm = gs('cm') or 'exact'
            if cur_cm not in cm_opts:
                cur_cm = 'exact'
            new_cm = st.selectbox('对比方式', [cm_labels[o] for o in cm_opts],
                                  index=cm_opts.index(cur_cm), key=pk+'w_cm')
            cm_val = cm_opts[[cm_labels[o] for o in cm_opts].index(new_cm)]
            if cm_val != cur_cm:
                ss_set('cm', cm_val)

        with c2:
            st.caption('')
            if st.button('↻ 重置模板', use_container_width=True, key=pk+'w_reset_tpl'):
                tpl = (problem.get('template') or
                      (isinstance(problem.get('templates'), dict) and problem['templates'].get(gs('lang'), ''))
                       or LANG_DEFAULT_CODE.get(gs('lang'), ''))
                ss_set('code', tpl)
                toast_safe('已重置为该语言默认模板', 'ok')
                st.rerun()

        r1, r2 = st.columns(2)
        with r1:
            tl_val = st.number_input('时间限制 (s)', min_value=0.1, max_value=60.0, step=0.1,
                                     value=float(gs('tl') or 1.0), key=pk+'w_tl')
        with r2:
            ml_val = st.number_input('内存限制 (MB)', min_value=8, max_value=2048, step=8,
                                     value=int(gs('ml') or 128), key=pk+'w_ml')

        cur_code = st.text_area('代码编辑器', value=gs('code') or '', height=360,
                                label_visibility='visible', key=pk+'w_code',
                                help='支持多语言。注意输入/输出走标准流。')

# 右列上：测试用例卡（tabs 分公开 / 自定义）+ 下：判题结果卡
with col_right:
    case_card = st.container(border=True)
    with case_card:
        st.subheader('📊 测试用例', divider=False)
        t1, t2 = st.tabs(['📋 一、公开样例（题目提供）', '🔥 二、自定义调试样例'])
        samples = problem.get('samples') or []
        with t1:
            use_s = st.checkbox('使用「公开样例」参与评测', value=gs('samples'), key=pk+'w_samples')
            if not samples:
                st.caption('（该题目暂未设置公开样例）')
            elif use_s:
                for i, s in enumerate(samples):
                    with st.expander(f'📑 公开样例 #{i+1}', expanded=(i == 0)):
                        c_in, c_out = st.columns(2)
                        with c_in:
                            st.caption('输入 Input')
                            st.code(s.get('input', '') or '', language=None)
                        with c_out:
                            st.caption('期望输出 Expected')
                            st.code(s.get('output', '') or '', language=None)
                        if s.get('explanation'):
                            st.caption(f'📝 样例解释')
                            st.info(s['explanation'])

        with t2:
            c_check1, c_check2, c_btn = st.columns([3, 4, 2])
            with c_check1:
                use_c = st.checkbox('使用自定义调试样例', value=gs('custom'), key=pk+'w_custom')
            with c_check2:
                only_c = st.checkbox('仅评测自定义样例', value=gs('only_custom'), key=pk+'w_only_custom')
            with c_btn:
                if st.button('＋ 新增一组', use_container_width=True, type='primary', key=pk+'w_add_custom'):
                    lst = list(gs('custom_list') or [])
                    lst.append({'input':'', 'output':''})
                    ss_set('custom_list', lst)
                    st.rerun()
            st.caption('⚠️ 自定义样例期望由你自己填写，系统按你写的对比，方便调试。')

            n_s = len(samples) if use_s else 0
            n_c = len(gs('custom_list') or []) if use_c else 0
            tag = '（仅自定义模式）' if only_c else ''
            st.caption(f'**评测范围预览**：{n_s} 个公开样例 + {n_c} 个自定义 = **{n_s+n_c}** 个测试点 {tag}')

            c_list = list(gs('custom_list') or [])
            changed_list = False
            if not c_list:
                st.caption('（暂无自定义样例，点击右上角「＋ 新增一组」）')
            else:
                new_list = []
                for i, case in enumerate(c_list):
                    with st.expander(f'🧪 自定义样例 #{i+1}', expanded=True):
                        ci, co, cd = st.columns([6, 6, 1])
                        with ci:
                            st.caption('输入 Input')
                            v = st.text_area(f'自定义输入 #{i+1}', value=case.get('input',''),
                                             height=90, label_visibility='collapsed',
                                             key=f'{pk}w_custom_in_{i}')
                            case_in = v
                        with co:
                            st.caption('期望输出 Expected')
                            v = st.text_area(f'自定义输出 #{i+1}', value=case.get('output',''),
                                             height=90, label_visibility='collapsed',
                                             key=f'{pk}w_custom_out_{i}')
                            case_out = v
                        with cd:
                            st.caption('')
                            if st.button('🗑 删除', key=f'{pk}w_del_custom_{i}', use_container_width=True):
                                changed_list = True
                                continue
                        new_list.append({'input': case_in, 'output': case_out})
                c_list = new_list
                if changed_list:
                    ss_set('custom_list', c_list)
                    st.rerun()
                else:
                    ss_set('custom_list', c_list)

    st.caption('')  # 间隔

    # 右列下：判题结果卡
    res_card = st.container(border=True)
    with res_card:
        r1, r2 = st.columns([7, 3])
        with r1:
            st.subheader('🏆 判题结果', divider=False)
        with r2:
            st.caption('')
            submit = st.button('▶ 提交判题', type='primary', use_container_width=True,
                               key=pk+'w_submit_btn')

        # 支持 URL 带 submission=xxx 直接载入
        force_sub = st.query_params.get('submission') or ''
        last = gs('last')
        def _sid(x):
            return (x or {}).get('id') or (x or {}).get('submission_id')
        if force_sub and (not last or str(_sid(last)) != str(force_sub)):
            with st.spinner('加载提交详情…'):
                c, d, _ = api('GET', f'/api/submissions/{force_sub}')
                if c == 200 and d and d.get('data'):
                    last = d['data']
                    ss_set('last', last)

        if submit:
            with st.spinner('⏳ 正在判题…'):
                payload = {
                    'problem_id': p_id,
                    'language': gs('lang'),
                    'code': cur_code or '',
                    'time_limit': float(tl_val),
                    'memory_limit': int(ml_val),
                    'compare_mode': gs('cm') or 'exact',
                }
                if use_s and samples:
                    payload['samples_override'] = [
                        {'input': s.get('input',''), 'expected': s.get('output','')}
                        for s in samples
                    ]
                if use_c and c_list:
                    payload['custom_cases'] = [
                        {'input': c.get('input',''), 'expected': c.get('output','')}
                        for c in c_list if (c.get('input') or c.get('output'))
                    ]
                if only_c:
                    payload['only_custom_cases'] = True
                c, d, err = api('POST', '/api/submissions/', payload)
                if c == 200 and d and d.get('data'):
                    sub = d['data']
                    sid = sub.get('id') or sub.get('submission_id')
                    if not sid:
                        st.error('后端未返回 submission_id：' + json.dumps(d, ensure_ascii=False)[:300])
                    else:
                        toast_safe('已提交，等待判题…', 'info')
                        waited = 0.0
                        pending_set = {'PENDING', 'RUNNING', 'JUDGING', 'pending', 'running', 'judging'}
                        while waited < 90:
                            c2, d2, _ = api('GET', f'/api/submissions/{sid}')
                            if c2 == 200 and d2 and d2.get('data'):
                                sub = d2['data']
                                s_stat = sub.get('status') or ''
                                if s_stat and s_stat not in pending_set:
                                    break
                            time.sleep(2.0)
                            waited += 2.0
                        ss_set('last', sub)
                        st.rerun()
                else:
                    st.error(f'提交失败：{d.get("msg") if d else err} (HTTP {c})')

        if not last:
            st.info('点击右上角「▶ 提交判题」开始运行代码。')
        else:
            raw_status = last.get('status') or '--'
            score = last.get('score') or 0
            total = last.get('total_cases') or 0
            passed = last.get('passed_cases') or 0
            counts = last.get('counts')
            if (not total or not passed) and counts:
                ri = last.get('run_info') or {}
                msg = ri.get('message') if isinstance(ri, dict) else (str(ri) or '')
                m = __import__('re').search(r'(\d+)\s+passed\s+of\s+(\d+)', msg or '')
                if m:
                    passed = int(m.group(1)); total = int(m.group(2))
                elif isinstance(counts, int) and counts > 0:
                    passed = total = counts
            if raw_status == 'success':
                status = 'AC'
            elif raw_status == 'pending' or raw_status in ('PENDING','RUNNING','JUDGING'):
                status = raw_status.upper() if raw_status.isalpha() else 'PENDING'
            else:
                status = raw_status
            t_ms = last.get('time_ms') or 0
            m_kb = last.get('memory_kb') or 0
            if not t_ms and isinstance(last.get('run_info'), dict):
                try: t_ms = int(last['run_info'].get('time_ms') or 0)
                except Exception: pass
            if not m_kb and isinstance(last.get('run_info'), dict):
                try: m_kb = int(last['run_info'].get('memory_kb') or 0)
                except Exception: pass
            m_mb = round(m_kb / 1024, 2) if m_kb else 0
            lang = last.get('language') or ''
            ct = last.get('created_at') or last.get('submit_time') or ''
            sid = _sid(last)

            def status_badge(s):
                if s == 'AC':
                    st.success('✅ AC (Accepted)')
                elif s in ('WA', 'RE', 'CE', 'SE', 'MLE'):
                    st.error(f'❌ {s}')
                elif s in ('TLE', 'OLE', 'PENDING', 'RUNNING', 'JUDGING'):
                    st.warning(f'⏱ {s}')
                else:
                    st.info(f'ℹ️ {s}')

            a, b, c1, d1 = st.columns(4)
            with a:
                status_badge(status)
                st.caption('最终状态')
            with b:
                st.metric('得分', f'{score} 分')
            with c1:
                st.metric('运行用时', f'{t_ms} ms')
            with d1:
                st.metric('内存使用', f'{m_mb} MB')

            max_score = (last.get('max_score') or 0) if isinstance(last.get('max_score'), (int, float)) else 0
            if isinstance(score, (int, float)) and score >= 0:
                denom = max_score if max_score > score and max_score > 0 else (100 if score <= 100 else max(100, score))
                st.progress(min(score / denom, 1.0) if denom > 0 else 0.0)
            st.caption(f'📋 Submission #{sid} · 语言 {lang} · 通过 {passed}/{total} 个测试点 · 提交于 {ct}')

            # 加载详情
            @st.cache_data(show_spinner=False, ttl=60)
            def load_detail(sid):
                c, d, _ = api('GET', f'/api/submissions/{sid}')
                if c == 200 and d and d.get('data'):
                    return d['data']
                return None

            detail = load_detail(str(sid))
            cases = None
            if detail:
                c3, d3, _ = api('GET', f'/api/submissions/{sid}/log')
                if c3 == 200 and isinstance(d3, dict) and isinstance(d3.get('data'), dict):
                    cases = d3['data'].get('details') or None

            if not cases:
                st.caption('（暂无逐测试点详情）')
            else:
                st.markdown('#### 逐个测试点详情')
                for i, cs in enumerate(cases):
                    if not isinstance(cs, dict):
                        continue
                    cs_status = cs.get('status') or cs.get('result') or '??'
                    cs_time = cs.get('time_ms') or cs.get('time') or 0
                    cs_mem_kb = cs.get('memory_kb') or 0
                    cs_mem_mb = round(cs_mem_kb / 1024, 2) if cs_mem_kb else round(float(cs.get('memory') or 0), 2)
                    cs_in = cs.get('input')
                    cs_exp = cs.get('expected')
                    cs_act = cs.get('actual')
                    cs_err = cs.get('stderr') or cs.get('error')
                    with st.expander(
                        f'#{i+1}  Test {i+1}   [{cs_status}]   ⏱ {cs_time}ms · 💾 {cs_mem_mb}MB',
                        expanded=(cs_status != 'AC')
                    ):
                        a, b = st.columns(2)
                        with a:
                            status_badge(cs_status)
                        with b:
                            st.caption(f'⏱ {cs_time} ms  ·  💾 {cs_mem_mb} MB')
                        if cs_in is not None:
                            st.caption('🔤 Input')
                            st.code(cs_in, language=None)
                        else:
                            st.info('🔒 无权查看该测试点 Input')
                        col_exp, col_act = st.columns(2)
                        with col_exp:
                            if cs_exp is not None:
                                st.caption('✅ Expected')
                                st.code(cs_exp, language=None)
                            else:
                                st.info('🔒 无权查看 Expected')
                        with col_act:
                            if cs_act is not None:
                                st.caption('💻 Actual')
                                st.code(cs_act, language=None)
                            else:
                                st.info('🔒 无权查看 Actual')
                        if cs_err:
                            st.caption('❌ 错误/异常')
                            st.code(cs_err, language=None)
                        if cs_status == 'WA' and cs_exp is not None and cs_act is not None:
                            with st.expander('🔍 Line-by-line Diff（期望 vs 实际）', expanded=True):
                                diff = list(difflib.unified_diff(
                                    (cs_exp or '').splitlines(keepends=True),
                                    (cs_act or '').splitlines(keepends=True),
                                    fromfile='Expected', tofile='Actual', lineterm=''
                                ))
                                if not diff:
                                    st.caption('内容逐行一致，可能是行尾空格/换行差异导致 WA，可切换 Trim 模式重试。')
                                else:
                                    st.code('\n'.join(diff), language='diff')

st.caption('© OJ 在线判题平台 · Streamlit 前端 + FastAPI 后端（Python 双栈架构）')
