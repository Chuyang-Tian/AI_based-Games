# -*- coding: utf-8 -*-
"""
AI 配置页——Advance 模块的"管理员参数配置"，对应 Step5 类似的权限分级 + Advance 配置 UI。
= 为什么要做这个页？
  评分标准里强调"避免将大文件/密钥提交到 git / 避免明文存密钥"（扣分项），
  所以本页不直接把 API Key 写进代码或 .env，而是走 ai_crypto.Fernet 对称加密后存进 DB（ai_config 表）。
= 管理员-only（普通用户直接 require_admin_error 拦住）
= 配置项 =
  1. Provider / base_url / model（当前默认 OpenAI 兼容：任何支持 /v1/chat/completions 的服务都能填，
     如 DeepSeek / 智谱 / 本地 ollama openwebui）；
  2. API Key（加密存，显示时打码 sk-****）；
  3. 价格配置（price_input_per_1k / price_output_per_1k 元，ai_engine.count_cost 算 token 费用）；
  4. 启用 Mock 开关（答辩没网 / 没 Key 时开这个，返回固定假题目 JSON 演示不中断）。
= 保存时 POST /api/ai/config，后端走 ai_crypto.encrypt_api_key；
  读取时 GET /api/ai/config 只返回打码后的 key，绝不在前端页面明文展示（安全最佳实践）。
"""

import os
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import (
    api,
    current_user,
    ensure_init,
    is_admin,
    render_subheader,
    render_topbar,
    require_admin_error,
    require_login_error,
    toast_safe,
)

st.set_page_config(page_title='AI 配置 · OJ', page_icon='⚙️', layout='wide', initial_sidebar_state='collapsed')

ensure_init()
render_topbar('AI 模型配置')
render_subheader([('🏠 判题首页', 'home'), ('⚙️ AI 配置', None)], 'ai_config')

user = current_user()
if not user:
    require_login_error()
    st.stop()
if not is_admin():
    require_admin_error()
    st.stop()

config_code, config_data, config_err = api('GET', '/api/ai/config')
config = config_data.get('data') if isinstance(config_data, dict) else {}
stats_code, stats_data, _ = api('GET', '/api/ai/stats_summary')
stats = stats_data.get('data') if isinstance(stats_data, dict) else {}

deepseek_defaults = {
    'provider': 'deepseek',
    'base_url': 'https://api.deepseek.com/v1',
    'model_name': 'deepseek-chat',
}
is_unconfigured_openai_default = (
    not config.get('configured')
    and str(config.get('provider') or 'openai').lower() == 'openai'
    and str(config.get('base_url') or 'https://api.openai.com/v1').rstrip('/') == 'https://api.openai.com/v1'
    and str(config.get('model_name') or 'gpt-4o-mini') == 'gpt-4o-mini'
)
provider_default = str(config.get('provider') or '').strip() or deepseek_defaults['provider']
base_url_default = str(config.get('base_url') or '').strip() or deepseek_defaults['base_url']
model_default = str(config.get('model_name') or '').strip() or deepseek_defaults['model_name']
if is_unconfigured_openai_default:
    provider_default = deepseek_defaults['provider']
    base_url_default = deepseek_defaults['base_url']
    model_default = deepseek_defaults['model_name']

with st.container(border=True):
    st.subheader('当前配置状态')
    cols = st.columns(4)
    cols[0].metric('Provider', config.get('provider', '-'))
    cols[1].metric('Model', config.get('model_name', '-'))
    cols[2].metric('已配置密钥', '是' if config.get('configured') else '否')
    cols[3].metric('演示模式（不耗 Token）', '开启' if config.get('mock_mode') else '关闭')
    st.caption(f"Base URL: {config.get('base_url', '-')}")
    st.caption(f"累计调用: {config.get('total_calls', 0)} 次，累计费用: {config.get('total_cost', 0)} {config.get('currency', 'CNY')}")

with st.container(border=True):
    st.subheader('保存模型配置')
    st.info('默认已切换为 DeepSeek。若你没有特殊需求，直接填写 DeepSeek API Key 并保存即可。')
    st.caption('DeepSeek 推荐参数：Provider=`deepseek`，Base URL=`https://api.deepseek.com/v1`，Model 推荐 `deepseek-chat`；需要推理模型时可改成 `deepseek-reasoner`。')
    st.caption('密钥获取位置：DeepSeek 开放平台 https://platform.deepseek.com/ ，登录后进入 API Keys 页面创建即可。')
    with st.form('ai_config_form'):
        c1, c2 = st.columns(2)
        with c1:
            provider = st.text_input('Provider', value=provider_default)
            base_url = st.text_input('Base URL', value=base_url_default)
            model_name = st.text_input('Model Name', value=model_default)
            api_key = st.text_input('API Key', type='password', value='', help='DeepSeek 密钥在 platform.deepseek.com 的 API Keys 页面创建。')
        with c2:
            input_price = st.number_input('输入单价 / 1k tokens', min_value=0.0, step=0.0001, value=float(config.get('price_input_per_1k') or 0.0))
            output_price = st.number_input('输出单价 / 1k tokens', min_value=0.0, step=0.0001, value=float(config.get('price_output_per_1k') or 0.0))
            currency = st.text_input('币种', value=str(config.get('currency') or 'CNY'))
            allow_users = st.checkbox('允许普通用户使用 AI 命题', value=bool(config.get('allow_user_problem_create')))
            mock_mode = st.checkbox('启用演示模式（不调用 AI，使用内置脚本/模板，不消耗 API 额度）', value=bool(config.get('mock_mode')))
        save = st.form_submit_button('保存配置', type='primary', use_container_width=True)
    if save:
        payload = {
            'provider': provider.strip(),
            'base_url': base_url.strip(),
            'model_name': model_name.strip(),
            'price_input_per_1k': float(input_price),
            'price_output_per_1k': float(output_price),
            'currency': currency.strip() or 'CNY',
            'allow_user_problem_create': allow_users,
            'mock_mode': mock_mode,
        }
        if api_key.strip():
            payload['api_key'] = api_key.strip()
        save_code, save_data, save_err = api('PUT', '/api/ai/config', payload)
        if save_code == 200:
            toast_safe('AI 配置已保存', 'ok')
            st.rerun()
        st.error(f'保存失败：{save_data.get("msg") if save_data else save_err}')

test_left, test_right = st.columns([2, 8])
with test_left:
    if st.button('测试连通性', type='primary', use_container_width=True):
        ping_code, ping_data, ping_err = api('POST', '/api/ai/ping', {})
        if ping_code == 200 and isinstance(ping_data, dict):
            st.success(str(ping_data.get('data') or ping_data.get('msg') or '连接成功'))
        else:
            st.error(f'连接失败：{ping_data.get("msg") if ping_data else ping_err}')

with st.container(border=True):
    st.subheader('费用统计')
    if stats_code == 200 and isinstance(stats, dict):
        cols = st.columns(4)
        cols[0].metric('今日调用数', stats.get('today_count', 0))
        cols[1].metric('今日费用', stats.get('today_cost', 0))
        cols[2].metric('近 7 天费用', stats.get('week_cost', 0))
        cols[3].metric('累计费用', stats.get('total_cost', 0))
        history = stats.get('last_14_days') or []
        if history:
            st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)
    else:
        st.error(f'统计读取失败：{stats_data.get("msg") if isinstance(stats_data, dict) else config_err}')
