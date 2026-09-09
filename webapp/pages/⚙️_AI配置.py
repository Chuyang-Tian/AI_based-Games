# -*- coding: utf-8 -*-
"""
⚙️ AI 配置中心（route_key=ai_config，仅 admin 进入）
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
st.set_page_config(page_title='AI配置 - OJ', page_icon='⚙️', layout='wide',
                   initial_sidebar_state='collapsed')

from common import (
    ensure_init, render_topbar, render_subheader,
    current_user, require_login_error, require_admin_error, is_admin,
    api, toast_safe,
)

ensure_init()
render_topbar('AI 配置中心')
render_subheader([
    ('🏠 判题首页', 'home'),
    ('⚙️ AI配置', None),
], 'ai_config')
user = current_user()

if not user:
    require_login_error()
    st.stop()

if not is_admin():
    require_admin_error()
    st.stop()

import pandas as pd

PROVIDERS = ['openai', 'anthropic', 'qwen', 'dashscope', 'gemini', 'openrouter', 'deepseek', 'glm', 'custom']

def load_ai_config():
    c, d, _ = api('GET', '/api/ai/config')
    if c == 200 and isinstance(d, dict) and d.get('data'):
        return d['data']
    c2, d2, _ = api('GET', '/api/ai/status')
    if c2 == 200 and isinstance(d2, dict) and d2.get('data'):
        return d2['data']
    return {}

cur_cfg = load_ai_config()

with st.container(border=True):
    st.subheader('🧠 当前 AI 配置状态')
    cur_provider = cur_cfg.get('provider') or '-'
    cur_model = cur_cfg.get('model') or '-'
    cur_base = cur_cfg.get('base_url') or '(默认官方)'
    is_configured = bool(cur_cfg.get('api_key') or cur_cfg.get('is_configured') or (cur_provider != '-' and cur_model != '-'))
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    col_s1.metric('Provider', cur_provider)
    col_s2.metric('模型 Model', cur_model)
    col_s3.metric('Base URL', cur_base[:40] + ('...' if len(cur_base) > 40 else ''))
    status_icon = '✅ 已配置' if is_configured else '⚠️ 未配置'
    col_s4.metric('密钥状态', status_icon)

with st.container(border=True):
    st.subheader('⚙️ 编辑 AI 配置')
    with st.form('ai_config_form'):
        a, b = st.columns(2)
        with a:
            cur_p = cur_cfg.get('provider', 'openai')
            p_idx = PROVIDERS.index(cur_p) if cur_p in PROVIDERS else 0
            cf_provider = st.selectbox('AI Provider', PROVIDERS, index=p_idx)
            cf_model = st.text_input('模型名 Model', value=str(cur_cfg.get('model') or ''),
                                    placeholder='如 gpt-4o / claude-3-5-sonnet / qwen-max / gemini-pro')
            cf_base_url = st.text_input('Base URL（空=官方默认）', value=str(cur_cfg.get('base_url') or ''),
                                       placeholder='自定义中转请填写，如 https://api.example.com/v1')
        with b:
            cur_masked = cur_cfg.get('api_key_masked') or cur_cfg.get('api_key') or ''
            cf_api_key = st.text_input('API Key', value='', type='password',
                                      placeholder='•••••• （留空=不修改现有 Key）',
                                      help='如果看到掩码星号，说明 Key 已存在；留空表示保留现有 Key；清空后保存会删除 Key。')
            cf_temp = st.number_input('temperature (0.0-2.0)', min_value=0.0, max_value=2.0, step=0.05,
                                      value=float(cur_cfg.get('temperature') or 0.7))
            cf_max_tokens = st.number_input('max_tokens（单次响应上限）', min_value=128, max_value=64000, step=256,
                                            value=int(cur_cfg.get('max_tokens') or 8192))
        c, d = st.columns(2)
        with c:
            cf_top_p = st.number_input('top_p (0.0-1.0)', min_value=0.0, max_value=1.0, step=0.05,
                                      value=float(cur_cfg.get('top_p') or 1.0))
        with d:
            st.caption('')
        submitted = st.form_submit_button('💾 保存配置', type='primary', use_container_width=True)

    if submitted:
        payload = {
            'provider': cf_provider,
            'model': cf_model,
            'base_url': cf_base_url or None,
            'temperature': float(cf_temp),
            'max_tokens': int(cf_max_tokens),
            'top_p': float(cf_top_p),
        }
        if cf_api_key:
            payload['api_key'] = cf_api_key
        write_ok = False
        cw, dw, errw = api('PUT', '/api/ai/config', payload)
        if cw == 200:
            write_ok = True
        if not write_ok:
            cw2, dw2, errw2 = api('PUT', '/api/admin/ai_config', payload)
            if cw2 == 200:
                write_ok = True
                cw, dw, errw = cw2, dw2, errw2
        if write_ok:
            toast_safe('✅ AI 配置已保存', 'ok')
            st.rerun()
        else:
            if cw == 404:
                toast_safe('当前后端暂未暴露 /api/ai/config 写接口，已记录但未持久化', 'warn')
                st.warning('⚠️ 提示：后端写接口暂未开放，本页面仅显示状态。可在 FastAPI 启动后启用写接口。')
            else:
                st.error(f'保存失败：{dw.get("msg") if dw else errw} ({cw})')

if st.button('🔌 测试连接（打 1 次 hello）', use_container_width=False):
    ct, dt, errt = api('POST', '/api/ai/test', {'echo': 'hello-oj-test'})
    if ct != 200:
        ct2, dt2, errt2 = api('POST', '/api/ai/ping', {'echo': 'hello-oj-test'})
        if ct2 == 200:
            ct, dt, errt = ct2, dt2, errt2
    if ct == 200 and dt:
        resp = ''
        if isinstance(dt.get('data'), dict):
            resp = str(dt['data'].get('response') or dt['data'].get('message') or dt['data'].get('ok') or '')
        elif isinstance(dt.get('data'), (str, int, float, bool)):
            resp = str(dt['data'])
        elif isinstance(dt, dict):
            resp = str(dt.get('msg') or dt.get('message') or dt)
        st.success(f'✅ AI 连通性测试通过：{resp[:120]}')
        toast_safe('连通性测试 OK', 'ok')
    else:
        st.error(f'❌ 连通失败：{dt.get("msg") if dt else errt} (code={ct})')

with st.container(border=True):
    st.subheader('📊 AI 使用量 & 调用记录')
    cu, du, _ = api('GET', '/api/ai/usage')
    if cu == 200 and isinstance(du, dict) and du.get('data'):
        u = du['data']
        m1, m2, m3, m4 = st.columns(4)
        m1.metric('🧠 总生成题目数', u.get('total_problems_generated') or 0)
        m2.metric('💰 累计 tokens 用量', u.get('total_tokens_used') or 0)
        cost = float(u.get('total_cost_usd') or 0)
        m3.metric('💰 累计费用(估计)', f'${cost:.4f}')
        last_time = str(u.get('last_call_time') or u.get('updated_at') or '-')[:19]
        m4.metric('📅 最近调用时间', last_time)
        history = u.get('recent_calls') or u.get('history') or u.get('logs') or []
        if history:
            st.caption('📋 最近调用记录')
            hrows = []
            for h in history:
                hrows.append({
                    '时间': str(h.get('created_at') or h.get('time') or '-')[:19],
                    '模式': h.get('mode') or h.get('gen_mode') or '-',
                    '题目数': h.get('problems_generated') or h.get('count') or 0,
                    'tokens': h.get('tokens') or h.get('tokens_used') or 0,
                    '耗时(ms)': h.get('latency_ms') or h.get('duration_ms') or 0,
                    '模型': h.get('model') or '-',
                })
            st.dataframe(pd.DataFrame(hrows), use_container_width=True, hide_index=True)
        else:
            st.caption('（暂无调用历史）')
    else:
        st.caption('（暂无使用数据，或后端未暴露 /api/ai/usage）')

st.caption('© OJ 在线判题平台 · Streamlit 前端 + FastAPI 后端（Python 双栈架构）')
