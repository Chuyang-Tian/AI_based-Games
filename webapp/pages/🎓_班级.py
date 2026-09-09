# -*- coding: utf-8 -*-
"""班级页面。"""

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common import (
    api,
    current_user,
    ensure_init,
    is_admin,
    page_url,
    render_home_button,
    render_page_link,
    render_subheader,
    render_topbar,
    require_login_error,
    toast_safe,
)

st.set_page_config(page_title='班级 · OJ', page_icon='🎓', layout='wide', initial_sidebar_state='collapsed')

ensure_init()
render_topbar('班级系统')

user = current_user()
if not user:
    require_login_error()
    st.stop()

raw_class_id = st.query_params.get('id') or ''
class_id = str(raw_class_id[0]) if isinstance(raw_class_id, list) and raw_class_id else str(raw_class_id or '')

if class_id:
    render_subheader([('🏠 判题首页', 'home'), ('🎓 班级', 'classes'), (f'班级 #{class_id}', None)], 'classes')
    code, data, err = api('GET', f'/api/classes/{class_id}')
    detail = data.get('data') if code == 200 and isinstance(data, dict) else None
    if not detail:
        st.error(f'班级加载失败：{data.get("msg") if isinstance(data, dict) else err}')
        render_home_button()
        st.stop()

    ass_code, ass_data, _ = api('GET', f'/api/classes/{class_id}/assignments')
    assignments = ass_data.get('data') if ass_code == 200 and isinstance(ass_data, dict) else []
    exam_code, exam_data, _ = api('GET', f'/api/classes/{class_id}/exams')
    exams = exam_data.get('data') if exam_code == 200 and isinstance(exam_data, dict) else []

    with st.container(border=True):
        left, right = st.columns([7, 2])
        with left:
            st.subheader(detail.get('class_name', ''), divider=False)
            st.caption(detail.get('description') or '暂无班级简介')
        with right:
            render_home_button()
        m1, m2, m3 = st.columns(3)
        m1.metric('成员数量', detail.get('member_count', 0))
        m2.metric('关联作业', len(assignments or []))
        m3.metric('关联考试', len(exams or []))

    tabs = st.tabs(['班级成员', '班级作业', '班级考试'] + (['管理班级'] if is_admin() else []))
    with tabs[0]:
        members = detail.get('members') or []
        if not members:
            st.info('暂无成员')
        else:
            for member in members:
                with st.container(border=True):
                    st.markdown(f"**#{member.get('user_id')} · {member.get('username')}**")
                    st.caption(f"角色：{member.get('role')}  |  加入时间：{member.get('joined_at') or '-'}")
    with tabs[1]:
        if not assignments:
            st.info('暂无关联作业')
        else:
            for item in assignments:
                with st.container(border=True):
                    left, right = st.columns([7, 2])
                    with left:
                        st.markdown(f"**作业 #{item.get('assignment_id')} · {item.get('title')}**")
                        st.caption(f"题目数：{item.get('problem_count')}  |  总分：{item.get('total_points')}  |  截止：{item.get('due_at') or '-'}")
                    with right:
                        render_page_link('进入作业', page_url('assignments', id=item.get('assignment_id')))
    with tabs[2]:
        if not exams:
            st.info('暂无关联考试')
        else:
            for item in exams:
                with st.container(border=True):
                    left, right = st.columns([7, 2])
                    with left:
                        st.markdown(f"**考试 #{item.get('exam_id')} · {item.get('title')}**")
                        st.caption(f"题目数：{item.get('problem_count')}  |  总分：{item.get('total_points')}  |  结束：{item.get('end_at') or '-'}")
                    with right:
                        render_page_link('进入考试', page_url('exams', id=item.get('exam_id')))

    if is_admin():
        with tabs[3]:
            with st.form('class_edit_form'):
                class_name = st.text_input('班级名称', value=detail.get('class_name', ''))
                description = st.text_area('班级描述', value=detail.get('description', ''), height=100)
                member_ids = st.text_input('新增成员用户 ID（逗号分隔）', placeholder='例如 2,3,4')
                member_usernames = st.text_input('新增成员用户名（逗号分隔）', placeholder='例如 stu_alice, stu_bob')
                remove_ids = st.text_input('移除成员用户 ID（逗号分隔）', placeholder='例如 5,6')
                c1, c2 = st.columns(2)
                save_clicked = c1.form_submit_button('保存班级', type='primary', use_container_width=True)
                delete_clicked = c2.form_submit_button('删除班级', use_container_width=True)

            if save_clicked:
                save_code, save_data, save_err = api('PUT', f'/api/classes/{class_id}', {'class_name': class_name, 'description': description})
                if save_code == 200:
                    add_list = [int(item.strip()) for item in member_ids.split(',') if item.strip().isdigit()]
                    add_usernames = [item.strip() for item in member_usernames.split(',') if item.strip()]
                    remove_list = [int(item.strip()) for item in remove_ids.split(',') if item.strip().isdigit()]
                    if add_list or add_usernames:
                        api('POST', f'/api/classes/{class_id}/members', {'user_ids': add_list, 'usernames': add_usernames})
                    if remove_list:
                        api('DELETE', f'/api/classes/{class_id}/members', {'user_ids': remove_list})
                    toast_safe('班级已更新', 'ok')
                    st.rerun()
                st.error(f'保存失败：{save_data.get("msg") if save_data else save_err}')
            if delete_clicked:
                del_code, del_data, del_err = api('DELETE', f'/api/classes/{class_id}')
                if del_code == 200:
                    toast_safe('班级已删除', 'ok')
                    render_page_link('返回班级列表', page_url('classes'))
                    st.stop()
                st.error(f'删除失败：{del_data.get("msg") if del_data else del_err}')
else:
    render_subheader([('🏠 判题首页', 'home'), ('🎓 班级', None)], 'classes')
    code, data, err = api('GET', '/api/classes')
    classes = data.get('data') if code == 200 and isinstance(data, dict) else []

    with st.container(border=True):
        top_left, top_right = st.columns([6, 2])
        with top_left:
            st.subheader('班级列表', divider=False)
            st.caption('这里展示当前用户可见的班级；点击进入后查看成员、作业和考试。')
        with top_right:
            render_home_button()

    if not classes:
        st.info('暂无班级数据')
    else:
        for item in classes:
            with st.container(border=True):
                left, right = st.columns([7, 2])
                with left:
                    st.markdown(f"**班级 #{item.get('class_id')} · {item.get('class_name')}**")
                    st.caption(f"成员数：{item.get('member_count', 0)}  |  {item.get('description') or '暂无简介'}")
                with right:
                    render_page_link('查看详情', page_url('classes', id=item.get('class_id')), primary=True)

    if is_admin():
        with st.expander('创建班级', expanded=False):
            with st.form('class_create_form'):
                class_name = st.text_input('班级名称')
                description = st.text_area('班级描述', height=100)
                create_clicked = st.form_submit_button('创建班级', type='primary', use_container_width=True)
            if create_clicked:
                create_code, create_data, create_err = api('POST', '/api/classes', {'class_name': class_name, 'description': description})
                if create_code == 200:
                    toast_safe('班级创建成功', 'ok')
                    st.rerun()
                st.error(f'创建失败：{create_data.get("msg") if create_data else create_err}')
