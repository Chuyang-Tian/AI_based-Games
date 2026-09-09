"""语言管理页（Step2 任务 3/4：动态注册新语言 + 查询语言列表）。"""
import os
import sys
import pandas as pd
import streamlit as st
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import OJ_VERSION, api, current_user, ensure_init, is_admin, load_languages, render_subheader, render_topbar, require_login_error, toast_safe, tr

def _fetch_full_languages():
    code, payload, _ = api('GET', '/api/languages')
    if code != 200 or not isinstance(payload, dict):
        return []
    data = payload.get('data')
    if isinstance(data, dict) and isinstance(data.get('list'), list):
        return data['list']
    if isinstance(data, list):
        rows = []
        for item in data:
            if isinstance(item, dict):
                rows.append(item)
        return rows
    return []

def _to_display_rows(langs, admin_view: bool):
    rows = []
    for item in langs:
        if not isinstance(item, dict):
            continue
        if not admin_view and (not bool(item.get('enabled', True))):
            continue
        rows.append({'name': str(item.get('name', '')), 'enabled': bool(item.get('enabled', True)), 'file_ext': str(item.get('file_ext', '')), 'compile_cmd': str(item.get('compile_cmd') or ''), 'run_cmd': str(item.get('run_cmd', '')), 'default_time_limit': item.get('default_time_limit'), 'default_memory_limit': item.get('default_memory_limit'), 'sort_order': item.get('sort_order'), 'is_builtin': bool(item.get('is_builtin', False)), 'created_at': str(item.get('created_at') or '')})
    rows.sort(key=lambda r: (9999 if r['sort_order'] is None else int(r['sort_order']), r['name']))
    return rows
st.set_page_config(page_title='语言管理 · OJ', page_icon='🔣', layout='wide', initial_sidebar_state='collapsed')
ensure_init()
render_topbar('语言中心')
render_subheader([('🏠 判题首页', 'home'), ('🔣 语言管理' if is_admin() else '🔣 语言列表', None)], 'languages')
user = current_user()
if not user:
    require_login_error()
    st.stop()
admin = is_admin()
st.markdown(f"""### 🔣 {tr('lang_title', '语言管理 / 列表')}  <span style="color:#9ca3af;font-size:14px;">（{OJ_VERSION}）</span>""", unsafe_allow_html=True)
if admin:
    with st.expander(tr('lang_register_expander', '➕ 注册一门新语言（所有已登录用户均可使用）'), expanded=False):
        with st.form('lang_create_form'):
            st.caption(tr('lang_register_hint', '提示：新增语言会对所有用户可见（TA-5 口径：语言列表 = 当前系统支持的所有编程语言，与 user_id 无关）。 编译命令中可使用占位符：{src}（源文件）、{bin}（可执行文件）、{python}（当前系统 Python）。'))
            c1, c2, c3 = st.columns(3)
            with c1:
                name = st.text_input(tr('lang_f_name', '语言标识名 (name，如 java、javascript、rust、go)'), placeholder='如 java、node、go、rust')
            with c2:
                file_ext = st.text_input(tr('lang_f_ext', '源文件扩展名 (file_ext，含点号)'), placeholder='如 .java、.js、.rs、.go')
            with c3:
                enabled_default = st.checkbox(tr('lang_f_enabled', '注册后立即可见'), value=True)
            run_cmd = st.text_input(tr('lang_f_run', '运行命令 (run_cmd，必填，可用占位符 {src}/{bin}/{python})'), placeholder='例: java -cp {dir} Main  或  node {src}  或  go run {src}  或  {bin}')
            compile_cmd = st.text_input(tr('lang_f_compile', '编译命令 (compile_cmd，解释型语言可留空，可用占位符 {src}/{bin}/{python})'), placeholder='例: g++ -O2 -std=c++17 {src} -o {bin}   或   javac -d {dir} {src}')
            c4, c5, c6 = st.columns(3)
            with c4:
                default_time_limit = st.number_input(tr('lang_f_tl', '默认时间限制 (秒)'), min_value=0.1, step=0.1, value=3.0)
            with c5:
                default_memory_limit = st.number_input(tr('lang_f_ml', '默认内存限制 (MB)'), min_value=8, step=8, value=128)
            with c6:
                sort_order = st.number_input(tr('lang_f_sort', '显示排序 (整数，小的靠前，0=默认)'), min_value=0, step=1, value=0)
            submitted = st.form_submit_button(tr('lang_submit', '注册并启用该语言'), type='primary', use_container_width=True)
        if submitted:
            if not name.strip() or not file_ext.strip() or (not run_cmd.strip()):
                st.error(tr('lang_err_required', 'name / file_ext / run_cmd 三项必填'))
            else:
                payload = {'name': name.strip(), 'file_ext': file_ext.strip(), 'run_cmd': run_cmd.strip(), 'default_time_limit': float(default_time_limit), 'default_memory_limit': int(default_memory_limit), 'enabled': bool(enabled_default), 'sort_order': int(sort_order)}
                if compile_cmd.strip():
                    payload['compile_cmd'] = compile_cmd.strip()
                code, resp, err = api('POST', '/api/languages', payload)
                if code == 200:
                    load_languages(force=True)
                    toast_safe(tr('lang_ok', '新语言注册成功，已对所有用户开放') if enabled_default else tr('lang_ok_hidden', '新语言注册成功（已设为不可见，管理员可稍后启用）'), 'ok')
                    st.rerun()
                msg = ''
                if isinstance(resp, dict):
                    msg = resp.get('msg') or ''
                st.error(f'注册失败 HTTP {code}: {msg or err}')
langs = _fetch_full_languages()
rows = _to_display_rows(langs, admin)
stats = st.columns(4)
stats[0].metric(tr('lang_m_total', '系统内语言总数'), str(len(langs)))
stats[1].metric(tr('lang_m_visible', '当前展示给普通用户'), str(sum((1 for r in rows if r.get('enabled')))))
stats[2].metric(tr('lang_m_builtin', '内置语言 (Python/C++)'), str(sum((1 for r in rows if r.get('is_builtin')))))
stats[3].metric(tr('lang_m_custom', '动态注册语言'), str(sum((1 for r in rows if not r.get('is_builtin')))))
with st.container(border=True):
    st.subheader(tr('lang_list_title', '语言明细表'))
    if not rows:
        st.info(tr('lang_empty', '当前没有可展示的语言，请先注册或联系管理员启用。'))
    else:
        df = pd.DataFrame(rows)
        df_show = df.rename(columns={'name': tr('col_name', '标识'), 'enabled': tr('col_enabled', '启用'), 'file_ext': tr('col_ext', '扩展名'), 'compile_cmd': tr('col_compile', '编译命令'), 'run_cmd': tr('col_run', '运行命令'), 'default_time_limit': tr('col_tl', '默认TL(s)'), 'default_memory_limit': tr('col_ml', '默认ML(MB)'), 'sort_order': tr('col_sort', '排序'), 'is_builtin': tr('col_builtin', '内置'), 'created_at': tr('col_created', '注册时间')})
        st.dataframe(df_show, use_container_width=True, hide_index=True, column_config={tr('col_enabled', '启用'): st.column_config.CheckboxColumn(disabled=True), tr('col_builtin', '内置'): st.column_config.CheckboxColumn(disabled=True)})
if admin:
    with st.expander(tr('lang_admin_switch', '🛡 管理员：启用 / 停用 语言开关'), expanded=False):
        if not rows:
            st.info(tr('lang_no_rows', '暂无语言可切换。'))
        else:
            opts = [r['name'] for r in rows]
            if not opts:
                st.info(tr('lang_no_rows', '暂无语言可切换。'))
            else:
                target_name = st.selectbox(tr('lang_which', '选择要切换的语言'), opts)
                current_enabled_map = {r['name']: r['enabled'] for r in rows}
                current_enabled = bool(current_enabled_map.get(target_name, True))
                new_enabled = st.checkbox(tr('lang_new_state', '切换后的状态（勾选=启用对所有用户可见，取消=停用仅管理员可操作）'), value=current_enabled)
                if st.button(tr('lang_apply_switch', '应用启用/停用状态'), type='primary', use_container_width=True):
                    code, resp, err = api('PUT', f'/api/languages/{target_name}/enabled', {'enabled': bool(new_enabled)})
                    if code == 200:
                        load_languages(force=True)
                        toast_safe(tr('lang_switched', '语言状态已更新'), 'ok')
                        st.rerun()
                    msg = ''
                    if isinstance(resp, dict):
                        msg = resp.get('msg') or ''
                    st.error(f'更新失败 HTTP {code}: {msg or err}')