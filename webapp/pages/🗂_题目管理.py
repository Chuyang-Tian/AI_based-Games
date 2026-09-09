# -*- coding: utf-8 -*-
"""
题目管理（Streamlit 原生组件版）：非管理员=题库浏览；管理员=题库+新建/编辑/删除
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
import pandas as pd

st.set_page_config(page_title='题目管理 · OJ', page_icon='🗂', layout='wide',
                   initial_sidebar_state='collapsed')

from common import (
    ensure_init, render_topbar, render_subheader,
    current_user, require_login_error, require_admin_error, is_admin,
    load_all_problems, get_filtered_problems, api, toast_safe, goto,
)

ensure_init()
render_topbar('题目管理（管理员可新建/编辑/删除）' if is_admin() else '题库浏览')
render_subheader([('🏠 判题首页', 'home'),
                  ('🗂 题目管理' if is_admin() else '📚 题库', None)], 'problems')

user = current_user()
if not user:
    require_login_error()
    st.stop()

is_adm = is_admin()
if is_adm:
    pass
else:
    st.caption('（当前非管理员：仅可浏览题库，跳转判题页）')

problems = load_all_problems()
if 'pm_diff' not in st.session_state:
    st.session_state['pm_diff'] = ''
if 'pm_tags' not in st.session_state:
    st.session_state['pm_tags'] = []
if 'pm_editing' not in st.session_state:
    st.session_state['pm_editing'] = None  # pid 或 None

if is_adm:
    # 管理入口条（新建 / 刷新）
    act_box = st.container(border=True)
    with act_box:
        a, b, c, d, e = st.columns([2, 2, 3, 2, 2])
        with a:
            st.metric('题库总数', f'{len(problems)}')
        with b:
            if st.button('＋ 新建题目', type='primary', use_container_width=True):
                st.session_state['pm_editing'] = '__NEW__'
                st.rerun()
        with c:
            kw = st.text_input('搜索题目（ID 或 标题）', value=st.session_state.get('pm_k', ''),
                               placeholder='按 ID 或标题搜…', label_visibility='collapsed')
            st.session_state['pm_k'] = kw
        with d:
            if st.button('🔄 刷新题库', use_container_width=True):
                load_all_problems(force=True)
                toast_safe('题库已刷新', 'ok')
                st.rerun()
        with e:
            if st.button('⬅ 回首页', use_container_width=True,
                         on_click=goto, kwargs={'route_key': 'home'}):
                pass

# 筛选
fb = st.container(border=True)
with fb:
    c1, c2, c3 = st.columns([2, 6, 3])
    with c1:
        st.caption('难度快捷')
        bs = st.columns(4)
        for i, (v, lab) in enumerate([('', '全部'), ('简单', '简单'), ('中等', '中等'), ('困难', '困难')]):
            active = (st.session_state['pm_diff'] == v)
            with bs[i]:
                if st.button(lab, type='primary' if active else 'secondary', use_container_width=True,
                             key=f'pmdff_{v or "all"}'):
                    st.session_state['pm_diff'] = v
                    st.rerun()
    with c2:
        pass  # 空占位
    with c3:
        all_tags = sorted({t for p in problems for t in (p.get('tags') or [])})
        if all_tags:
            st.caption('标签多选')
            sel = st.multiselect('标签多选', all_tags, default=st.session_state['pm_tags'],
                                 label_visibility='collapsed', key='pm_tag_ms')
            st.session_state['pm_tags'] = sel or []
        else:
            st.caption('（暂无标签）')

sel_tags = list(st.session_state.get('pm_tags') or [])
filtered = get_filtered_problems(problems, st.session_state.get('pm_k', ''),
                                 st.session_state.get('pm_diff', ''), sel_tags)
st.caption(f'共 **{len(filtered)}** 道题目匹配筛选。')

# ============ 新建/编辑 表单 ============
if st.session_state.get('pm_editing') and is_adm:
    is_new = (st.session_state['pm_editing'] == '__NEW__')
    if is_new:
        p_template = {
            'id': '', 'title': '', 'description': '',
            'input_description': '', 'output_description': '',
            'constraints': '', 'hint': '',
            'difficulty': '简单', 'tags': [], 'source': user.get('username') or 'admin',
            'author': user.get('username') or 'admin',
            'language': 'python',
            'time_limit': 1.0, 'memory_limit': 128,
            'compare_mode': 'exact',
            'template': '', 'templates': {},
            'samples': [{'input': '1 2\n', 'output': '3\n', 'explanation': '读 1 2 → 加和输出 3'}],
            'test_cases': [],
            'enabled': True,
            'is_public': True,
            'perm_mask': 0,
            'class_id': None, 'assignment_id': None, 'exam_id': None,
        }
    else:
        pid = st.session_state['pm_editing']
        c, d, _ = api('GET', f'/api/problems/{pid}')
        p_template = (d.get('data') if c == 200 and isinstance(d, dict) and d.get('data')
                      else next((p for p in problems if p.get('id') == pid), {}))

    edit_box = st.container(border=True)
    with edit_box:
        st.subheader('➕ 新建题目' if is_new else f'✏️ 编辑题目 `{p_template.get("id","")}`', divider=False)
        with st.form('pm_edit_form', clear_on_submit=False):
            f1, f2, f3, f4 = st.columns(4)
            with f1:
                nid = st.text_input('题目 ID（英文，不可含空格，新建必填）',
                                    value=p_template.get('id') or '',
                                    disabled=(not is_new))
            with f2:
                ntitle = st.text_input('题目标题', value=p_template.get('title') or '')
            with f3:
                diffs = ['简单', '中等', '困难']
                ndiff = st.selectbox('难度', diffs,
                                     index=diffs.index(p_template.get('difficulty') or '简单'))
            with f4:
                lang_opts = ['python', 'cpp', 'java', 'js', 'multi']
                nlang = st.selectbox('语言', lang_opts,
                                     index=lang_opts.index(p_template.get('language') or 'python'))
            r1, r2, r3 = st.columns([2, 2, 3])
            with r1:
                ntl = st.number_input('时间限制 (s)', min_value=0.1, max_value=60.0, step=0.1,
                                      value=float(p_template.get('time_limit') or 1.0))
            with r2:
                nml = st.number_input('内存限制 (MB)', min_value=8, max_value=2048, step=8,
                                      value=int(p_template.get('memory_limit') or 128))
            with r3:
                cm_opts = ['exact', 'trim', 'numeric']
                cm_labels = {'exact':'精确(行对比)', 'trim':'Trim 去首尾空格', 'numeric':'数值容差'}
                ncm = st.selectbox('对比方式', [cm_labels[k] for k in cm_opts],
                                   index=cm_opts.index(p_template.get('compare_mode') or 'exact'))
                ncm_val = cm_opts[[cm_labels[k] for k in cm_opts].index(ncm)]
            ndesc = st.text_area('题目描述', value=p_template.get('description') or '', height=180)
            g1, g2 = st.columns(2)
            with g1:
                nind = st.text_area('输入描述', value=p_template.get('input_description') or '', height=120)
            with g2:
                noutd = st.text_area('输出描述', value=p_template.get('output_description') or '', height=120)
            g1, g2 = st.columns(2)
            with g1:
                ncons = st.text_area('数据范围 / 约束（可选）', value=p_template.get('constraints') or '', height=100)
            with g2:
                nhint = st.text_area('提示（可选）', value=p_template.get('hint') or '', height=100)
            h1, h2, h3 = st.columns(3)
            with h1:
                nauthor = st.text_input('作者', value=p_template.get('author') or user.get('username') or 'admin')
            with h2:
                nsource = st.text_input('来源（class/exam/…）', value=p_template.get('source') or '')
            with h3:
                all_tags_here = sorted(set([t for p in problems for t in (p.get('tags') or [])] +
                                           list(p_template.get('tags') or [])))
                ntag = st.multiselect('标签（多选，可新增手写）', all_tags_here,
                                      default=list(p_template.get('tags') or []))
                free_tags = st.text_input('额外标签（逗号分隔，直接输入）', '')
                if free_tags:
                    for t in free_tags.split(','):
                        t = t.strip()
                        if t and t not in ntag:
                            ntag.append(t)
            tpl_languages = ['python', 'cpp', 'java', 'js']
            st.markdown('##### 语言模板（可选，留空则使用默认模板）')
            tpl_cols = st.columns(len(tpl_languages))
            templates_map = {}
            existing_tpls = p_template.get('templates') or {}
            for idx, lg in enumerate(tpl_languages):
                with tpl_cols[idx]:
                    tpl_default = (isinstance(existing_tpls, dict) and existing_tpls.get(lg, '')) or ''
                    if lg == 'python' and not tpl_default:
                        tpl_default = '# Python 模板\nimport sys\nfor line in sys.stdin:\n    ...\n'
                    templates_map[lg] = st.text_area(f'{lg} 模板', value=tpl_default, height=140,
                                                     key=f'tpl_{lg}')
            st.markdown('##### 公开样例 JSON 数组（每一项: {input, output, explanation?}）')
            samples = p_template.get('samples') or []
            ns_text = st.text_area('样例 JSON（JSON 数组）', height=160,
                                   value=json.dumps(samples, ensure_ascii=False, indent=2))
            st.markdown('##### 隐藏测试用例 JSON（可选，按权限查看）格式同上')
            tcs = p_template.get('test_cases') or []
            ntc_text = st.text_area('隐藏测试用例 JSON（JSON 数组）', height=140,
                                    value=json.dumps(tcs, ensure_ascii=False, indent=2))
            k1, k2, k3 = st.columns([3, 3, 3])
            with k1:
                nenabled = st.checkbox('启用', value=bool(p_template.get('enabled', True)))
            with k2:
                npublic = st.checkbox('公开（学生可见）', value=bool(p_template.get('is_public', True)))
            with k3:
                nperm = st.number_input('权限位掩码 perm_mask（0=默认）', min_value=0, max_value=31, step=1,
                                        value=int(p_template.get('perm_mask') or 0))
            s1, s2 = st.columns(2)
            with s1:
                if st.form_submit_button('💾 保存', type='primary', use_container_width=True):
                    # 校验
                    if not nid.strip():
                        st.error('题目 ID 不能为空')
                    elif not ntitle.strip():
                        st.error('题目标题不能为空')
                    else:
                        try:
                            sample_obj = json.loads(ns_text or '[]')
                            if not isinstance(sample_obj, list):
                                raise ValueError('样例必须是数组')
                        except Exception as e:
                            st.error(f'样例 JSON 解析失败：{e}')
                            sample_obj = None
                        try:
                            tc_obj = json.loads(ntc_text or '[]')
                            if not isinstance(tc_obj, list):
                                raise ValueError('隐藏测试用例必须是数组')
                        except Exception as e:
                            st.error(f'隐藏测试用例 JSON 解析失败：{e}')
                            tc_obj = None
                        if sample_obj is not None and tc_obj is not None:
                            payload = {
                                'id': nid.strip(),
                                'title': ntitle.strip(),
                                'description': ndesc or '',
                                'input_description': nind or '',
                                'output_description': noutd or '',
                                'constraints': ncons or '',
                                'hint': nhint or '',
                                'difficulty': ndiff,
                                'tags': ntag or [],
                                'author': nauthor.strip() or 'admin',
                                'source': nsource.strip() or '',
                                'language': nlang,
                                'time_limit': float(ntl),
                                'memory_limit': int(nml),
                                'compare_mode': ncm_val,
                                'template': templates_map.get('python', ''),
                                'templates': templates_map,
                                'samples': sample_obj,
                                'test_cases': tc_obj,
                                'enabled': bool(nenabled),
                                'is_public': bool(npublic),
                                'perm_mask': int(nperm),
                                'class_id': p_template.get('class_id'),
                                'assignment_id': p_template.get('assignment_id'),
                                'exam_id': p_template.get('exam_id'),
                            }
                            if is_new:
                                c, d, e = api('POST', '/api/problems/', payload)
                            else:
                                c, d, e = api('PUT', f'/api/problems/{nid.strip()}', payload)
                            if c in (200, 201) and d:
                                toast_safe('保存成功', 'ok')
                                load_all_problems(force=True)
                                st.session_state['pm_editing'] = None
                                st.rerun()
                            else:
                                st.error(f'保存失败 (HTTP {c})：{d.get("msg") if d else e}')
            with s2:
                if st.form_submit_button('取消', use_container_width=True):
                    st.session_state['pm_editing'] = None
                    st.rerun()

# ============ 题目列表 ============
if not filtered:
    st.info('（没有匹配的题目）')
else:
    list_box = st.container(border=True)
    with list_box:
        st.subheader('📚 题目列表' + ('（管理员：点击行右侧操作按钮编辑/删除/判题）' if is_adm else '（点击「➜ 判题」进入判题页）'),
                     divider=False)
        rows = []
        for p in filtered:
            rows.append({
                'ID': p.get('id'), '标题': p.get('title') or '',
                '难度': p.get('difficulty') or '', '作者': p.get('author') or '',
                '来源': p.get('source') or '', '语言': p.get('language') or '',
                '标签': ', '.join(p.get('tags') or []),
                '公开': '✅' if p.get('is_public') else '🔒',
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=520)
        # 操作选择条：选 ID → 判题/编辑/删除
        op_box = st.container(border=True)
        with op_box:
            opts = [f'{r["ID"]}  |  {r["标题"][:40]}' for r in rows]
            default_idx = 0 if opts else None
            if opts:
                col_sel, col_a, col_b, col_c = st.columns([6, 2, 2, 2])
                with col_sel:
                    picked = st.selectbox('操作对象（选中一道题）', opts,
                                          index=default_idx if default_idx is not None else 0)
                    pick_pid = rows[opts.index(picked)]['ID']
                with col_a:
                    st.caption('')
                    if st.button('➜ 判题', type='primary', use_container_width=True,
                                 on_click=goto, kwargs={'route_key': 'judge', 'id': pick_pid}):
                        pass
                with col_b:
                    st.caption('')
                    if st.button('✏️ 编辑', use_container_width=True, disabled=(not is_adm)):
                        if is_adm:
                            st.session_state['pm_editing'] = pick_pid
                            st.rerun()
                with col_c:
                    st.caption('')
                    if st.button('🗑 删除', use_container_width=True, disabled=(not is_adm)):
                        if is_adm:
                            if 'pm_del_confirm' not in st.session_state or st.session_state.get('pm_del_confirm') != pick_pid:
                                st.session_state['pm_del_confirm'] = pick_pid
                                st.warning(f'⚠️ 确认删除 `{pick_pid}`？请再次点击「🗑 删除」确认。')
                            else:
                                c, d, e = api('DELETE', f'/api/problems/{pick_pid}')
                                if c in (200, 204):
                                    toast_safe(f'已删除 {pick_pid}', 'ok')
                                    load_all_problems(force=True)
                                    st.session_state['pm_del_confirm'] = None
                                    st.rerun()
                                else:
                                    st.error(f'删除失败 (HTTP {c})：{d.get("msg") if d else e}')
            else:
                st.caption('（列表为空，无法操作）')

st.caption('© OJ 在线判题平台 · Streamlit 前端 + FastAPI 后端（Python 双栈架构）')
