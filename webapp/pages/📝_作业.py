"""作业页面。"""
import os
import sys
import streamlit as st
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import api, current_user, ensure_init, is_admin, page_url, render_home_button, render_page_link, render_subheader, render_topbar, require_login_error, toast_safe
st.set_page_config(page_title='作业 · OJ', page_icon='📝', layout='wide', initial_sidebar_state='collapsed')
ensure_init()
render_topbar('作业系统')
user = current_user()
if not user:
    require_login_error()
    st.stop()
raw_assignment_id = st.query_params.get('id') or ''
assignment_id = str(raw_assignment_id[0]) if isinstance(raw_assignment_id, list) and raw_assignment_id else str(raw_assignment_id or '')
if assignment_id:
    render_subheader([('🏠 判题首页', 'home'), ('📝 作业', 'assignments'), (f'作业 #{assignment_id}', None)], 'assignments')
    code, data, err = api('GET', f'/api/assignments/{assignment_id}')
    detail = data.get('data') if code == 200 and isinstance(data, dict) else None
    me_code, me_data, _ = api('GET', f'/api/assignments/{assignment_id}/me')
    my_status = me_data.get('data') if me_code == 200 and isinstance(me_data, dict) else {}
    if not detail:
        st.error(f"作业加载失败：{(data.get('msg') if isinstance(data, dict) else err)}")
        render_home_button()
        st.stop()
    with st.container(border=True):
        left, right = st.columns([7, 2])
        with left:
            st.subheader(detail.get('title', ''))
            st.caption(detail.get('description') or '暂无作业说明')
        with right:
            render_home_button()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric('题目数量', detail.get('problem_count', 0))
        m2.metric('总分', detail.get('total_points', 0))
        m3.metric('开始时间', detail.get('start_at') or '-')
        m4.metric('截止时间', detail.get('due_at') or '-')
    if my_status:
        with st.container(border=True):
            s1, s2, s3 = st.columns(3)
            s1.metric('当前得分', my_status.get('score', my_status.get('total_score', 0)))
            s2.metric('已完成题数', my_status.get('solved_count', 0))
            s3.metric('提交次数', my_status.get('submit_count', 0))
    st.markdown('#### 题目列表')
    problems = detail.get('problem_order') or []
    if not problems:
        st.info('该作业暂无题目')
    else:
        for item in problems:
            pid = item.get('problem_id')
            with st.container(border=True):
                left, mid, right = st.columns([6, 2, 2])
                with left:
                    title_text = item.get('title') or pid or '未命名题目'
                    order_value = item.get('order') or item.get('order_index') or '-'
                    st.markdown(f'**{pid} · {title_text}**')
                    st.caption(f"分值：{item.get('points', 0)}  |  顺序：{order_value}")
                with mid:
                    render_page_link('题目详情', page_url('problem_detail', id=pid))
                with right:
                    render_page_link('进入做题', page_url('judge', id=pid, assignment_id=assignment_id), primary=True)
    if is_admin():
        with st.expander('管理作业', expanded=False):
            with st.form('assignment_update_form'):
                title = st.text_input('标题', value=detail.get('title', ''))
                description = st.text_area('描述', value=detail.get('description', ''), height=100)
                published = st.checkbox('已发布', value=bool(detail.get('published', False)))
                c1, c2 = st.columns(2)
                save_clicked = c1.form_submit_button('保存作业', type='primary', use_container_width=True)
                delete_clicked = c2.form_submit_button('删除作业', use_container_width=True)
            if save_clicked:
                save_code, save_data, save_err = api('PUT', f'/api/assignments/{assignment_id}', {'title': title, 'description': description, 'published': published})
                if save_code == 200:
                    toast_safe('作业已更新', 'ok')
                    st.rerun()
                st.error(f"保存失败：{(save_data.get('msg') if save_data else save_err)}")
            if delete_clicked:
                del_code, del_data, del_err = api('DELETE', f'/api/assignments/{assignment_id}')
                if del_code == 200:
                    toast_safe('作业已删除', 'ok')
                    render_page_link('返回作业列表', page_url('assignments'))
                    st.stop()
                st.error(f"删除失败：{(del_data.get('msg') if del_data else del_err)}")
else:
    render_subheader([('🏠 判题首页', 'home'), ('📝 作业', None)], 'assignments')
    code, data, err = api('GET', '/api/assignments')
    assignments = data.get('data') if code == 200 and isinstance(data, dict) else []
    with st.container(border=True):
        left, right = st.columns([6, 2])
        with left:
            st.subheader('作业列表')
            st.caption('保留你的创新功能入口：班级下发作业、作业详情、面向作业上下文做题。')
        with right:
            render_home_button()
    if not assignments:
        st.info('暂无作业数据')
    else:
        for item in assignments:
            with st.container(border=True):
                left, right = st.columns([7, 2])
                with left:
                    st.markdown(f"**作业 #{item.get('assignment_id')} · {item.get('title')}**")
                    st.caption(f"题目数：{item.get('problem_count')}  |  总分：{item.get('total_points')}  |  截止：{item.get('due_at') or '-'}")
                with right:
                    render_page_link('查看作业', page_url('assignments', id=item.get('assignment_id')), primary=True)
    if is_admin():
        classes_code, classes_data, _ = api('GET', '/api/classes')
        classes = classes_data.get('data') if classes_code == 200 and isinstance(classes_data, dict) else []
        probs_code, probs_data, _ = api('GET', '/api/problems')
        problems = probs_data.get('data') if probs_code == 200 and isinstance(probs_data, dict) else []
        class_options = {f"#{item.get('class_id')} · {item.get('class_name')}": int(item.get('class_id')) for item in classes or []}
        problem_options = {f"{item.get('id')} · {item.get('title') or item.get('id')}": str(item.get('id')) for item in problems or []}
        with st.expander('创建作业', expanded=False):
            with st.form('assignment_create_form'):
                title = st.text_input('作业标题')
                description = st.text_area('作业说明', height=100)
                selected_classes = st.multiselect('面向班级', list(class_options.keys()))
                selected_problems = st.multiselect('题目列表', list(problem_options.keys()))
                point_each = st.number_input('每题分值', min_value=1, max_value=100, value=50, step=5)
                start_at = st.text_input('开始时间', value='2020-01-01 00:00:00')
                due_at = st.text_input('截止时间', value='2099-12-31 23:59:59')
                published = st.checkbox('立即发布', value=True)
                created = st.form_submit_button('创建作业', type='primary', use_container_width=True)
            if created:
                payload = {'title': title.strip(), 'description': description, 'audience_classes': [class_options[key] for key in selected_classes], 'problem_order': [{'problem_id': problem_options[key], 'points': int(point_each), 'order': idx + 1} for idx, key in enumerate(selected_problems)], 'start_at': start_at.strip() or None, 'due_at': due_at.strip() or None, 'published': published}
                create_code, create_data, create_err = api('POST', '/api/assignments', payload)
                if create_code == 200:
                    toast_safe('作业创建成功', 'ok')
                    st.rerun()
                st.error(f"创建失败：{(create_data.get('msg') if create_data else create_err)}")