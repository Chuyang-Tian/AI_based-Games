import sys
import os
import json
import uuid

from flask import Flask, render_template, request, jsonify, make_response, redirect, url_for

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from oj_judge import (
    JudgeStatus,
    Language,
    TestCase,
    Judger,
)
from userdb import (
    UserDatabase,
    USER_ROLE_ADMIN,
    USER_ROLE_USER,
    USER_ROLE_BANNED,
    VALID_ROLES,
    INITIAL_ADMIN_USERNAME,
    INITIAL_ADMIN_PASSWORD,
)


app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['JSON_AS_ASCII'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.secret_key = 'oj-debug-platform-secret-key-' + uuid.uuid4().hex


SESSION_COOKIE_NAME = 'oj_session_id'
db = UserDatabase()


def _load_problems_brief_view():
    result = []
    for p in db.list_problems_brief():
        item = {
            'id': p.get('id'),
            'title': p.get('title'),
            'difficulty': p.get('difficulty', ''),
            'tags': p.get('tags', []),
            'description': p.get('description', ''),
            'time_limit': p.get('time_limit', 1.0),
            'memory_limit': p.get('memory_limit', 128),
        }
        result.append(item)
    return result


def _session_id_from_req() -> str:
    return request.cookies.get(SESSION_COOKIE_NAME, '') or request.headers.get(
        'X-' + SESSION_COOKIE_NAME, ''
    )


def current_user():
    sid = _session_id_from_req()
    return db.get_session_user(sid)


def _login_response(user_id: int):
    sid = db.create_session(user_id)
    u = db.get_user_by_id(user_id)
    data_obj = {'session_id': sid}
    if u:
        data_obj.update({
            'user_id': str(u.user_id),
            'username': u.username,
            'role': u.role,
            'is_admin': u.role == USER_ROLE_ADMIN,
            'join_time': u.join_time,
            'submit_count': u.submit_count,
            'resolve_count': u.resolve_count,
        })
    resp = make_response(jsonify({'code': 200, 'msg': '登录成功', 'data': data_obj}))
    resp.set_cookie(
        SESSION_COOKIE_NAME, sid,
        max_age=7 * 24 * 3600,
        httponly=True,
        samesite='Lax',
    )
    return resp


def require_login(allow_admin_only: bool = False):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                return jsonify({'code': 401, 'msg': '请先登录'}), 401
            if allow_admin_only and user.role != USER_ROLE_ADMIN:
                return jsonify({'code': 403, 'msg': '权限不足，仅管理员可操作'}), 403
            return fn(user, *args, **kwargs)
        wrapper.__name__ = fn.__name__ + '_auth'
        return wrapper
    return decorator


def serialize_result(result):
    case_results = []
    for cr in result.case_results:
        case_results.append({
            'case_id': cr.case_id,
            'status': cr.status.value,
            'status_desc': cr.status.description,
            'input_data': cr.input_data,
            'expected_output': cr.expected_output,
            'actual_output': cr.actual_output,
            'time_ms': round(cr.time_used * 1000, 2),
            'memory_mb': round(cr.memory_used, 2),
            'error_message': cr.error_message,
            'is_sample': cr.is_sample,
        })
    return {
        'summary': result.summary(),
        'error_message': result.error_message,
        'compile_message': result.compile_message,
        'case_results': case_results,
    }


def _user_public_viewer(user, viewer=None):
    pub = user.to_public()
    is_self = viewer and viewer.user_id == user.user_id
    is_admin = viewer and viewer.role == USER_ROLE_ADMIN
    if is_self or is_admin:
        pass
    return pub


# ========================== 页面路由 ==========================

@app.route('/')
def index():
    problems = _load_problems_brief_view()
    user = current_user()
    user_info = None
    if user:
        user_info = {
            'user_id': str(user.user_id),
            'username': user.username,
            'role': user.role,
            'is_admin': user.role == USER_ROLE_ADMIN,
        }
    return render_template('index.html', problems=problems, current_user=user_info)


@app.route('/users')
def page_users():
    user = current_user()
    if not user:
        return redirect(url_for('index'))
    if user.role != USER_ROLE_ADMIN:
        return redirect(url_for('index'))
    problems = _load_problems_brief_view()
    user_info = {
        'user_id': str(user.user_id),
        'username': user.username,
        'role': user.role,
        'is_admin': True,
    }
    return render_template('users.html', problems=problems, current_user=user_info)


@app.route('/problems')
def page_problems():
    user = current_user()
    if not user:
        return redirect(url_for('index'))
    if user.role != USER_ROLE_ADMIN:
        return redirect(url_for('index'))
    problems = _load_problems_brief_view()
    user_info = {
        'user_id': str(user.user_id),
        'username': user.username,
        'role': user.role,
        'is_admin': True,
    }
    return render_template('problems.html', problems=problems, current_user=user_info)


# ========================== 用户 API ==========================

@app.route('/api/auth/me')
def api_auth_me():
    user = current_user()
    if not user:
        return jsonify({'code': 401, 'msg': '未登录', 'data': None})
    return jsonify({
        'code': 200,
        'msg': 'success',
        'data': {
            'user_id': str(user.user_id),
            'username': user.username,
            'role': user.role,
            'join_time': user.join_time,
            'submit_count': user.submit_count,
            'resolve_count': user.resolve_count,
            'is_admin': user.role == USER_ROLE_ADMIN,
        },
    })


@app.route('/api/auth/register', methods=['POST'])
def api_register():
    data = request.get_json(force=True, silent=True) or {}
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '')
    role = data.get('role', USER_ROLE_USER)

    if not username:
        return jsonify({'code': 400, 'msg': '用户名不能为空'}), 400
    if len(username) < 3 or len(username) > 40:
        return jsonify({'code': 400, 'msg': '用户名长度需在 3-40 字符之间'}), 400
    if len(password) < 6:
        return jsonify({'code': 400, 'msg': '密码长度至少 6 位'}), 400
    if role not in VALID_ROLES:
        role = USER_ROLE_USER

    caller = current_user()
    if role == USER_ROLE_ADMIN:
        if not caller or caller.role != USER_ROLE_ADMIN:
            return jsonify({'code': 403, 'msg': '仅管理员可注册管理员账号'}), 403

    user = db.create_user(username, password, role if role != USER_ROLE_BANNED else USER_ROLE_USER)
    if not user:
        existing = db.get_user_by_username(username)
        if existing:
            return jsonify({'code': 409, 'msg': '用户名已存在'}), 409
        return jsonify({'code': 400, 'msg': '注册失败，请检查输入'}), 400

    return _login_response(user.user_id)


@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json(force=True, silent=True) or {}
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '')
    if not username or not password:
        return jsonify({'code': 400, 'msg': '用户名和密码不能为空'}), 400
    user = db.verify_user_login(username, password)
    if not user:
        maybe = db.get_user_by_username(username)
        if maybe and maybe.role == USER_ROLE_BANNED:
            return jsonify({'code': 403, 'msg': '账号已被封禁，无法登录'}), 403
        return jsonify({'code': 401, 'msg': '用户名或密码错误'}), 401
    return _login_response(user.user_id)


@app.route('/api/auth/logout', methods=['POST', 'GET'])
def api_logout():
    sid = _session_id_from_req()
    db.delete_session(sid)
    resp = make_response(jsonify({'code': 200, 'msg': '登出成功'}))
    resp.delete_cookie(SESSION_COOKIE_NAME)
    return resp


@app.route('/api/user/<user_id_or_me>')
def api_user_info(user_id_or_me):
    viewer = current_user()
    if user_id_or_me == 'me':
        if not viewer:
            return jsonify({'code': 401, 'msg': '请先登录'}), 401
        target = viewer
    else:
        try:
            uid = int(user_id_or_me)
        except (ValueError, TypeError):
            return jsonify({'code': 400, 'msg': '无效的 user_id'}), 400
        target = db.get_user_by_id(uid)
        if not target:
            return jsonify({'code': 404, 'msg': '用户不存在'}), 404
        if not viewer:
            return jsonify({'code': 401, 'msg': '请先登录'}), 401
        if viewer.role != USER_ROLE_ADMIN and viewer.user_id != target.user_id:
            return jsonify({'code': 403, 'msg': '权限不足'}), 403

    return jsonify({
        'code': 200,
        'msg': 'success',
        'data': target.to_public(),
    })


@app.route('/api/users')
def api_user_list():
    viewer = current_user()
    if not viewer:
        return jsonify({'code': 401, 'msg': '请先登录'}), 401
    if viewer.role != USER_ROLE_ADMIN:
        return jsonify({'code': 403, 'msg': '仅管理员可查询用户列表'}), 403

    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
    except ValueError:
        return jsonify({'code': 400, 'msg': 'page / page_size 必须为整数'}), 400
    keyword = request.args.get('keyword') or None

    total, users = db.list_users(page=page, page_size=page_size, keyword=keyword)
    return jsonify({
        'code': 200,
        'msg': 'success',
        'data': {
            'total': total,
            'page': page,
            'page_size': page_size,
            'users': [u.to_public() for u in users],
        },
    })


@app.route('/api/user/<int:user_id>/role', methods=['PUT'])
def api_update_role(user_id):
    viewer = current_user()
    if not viewer:
        return jsonify({'code': 401, 'msg': '请先登录'}), 401
    if viewer.role != USER_ROLE_ADMIN:
        return jsonify({'code': 403, 'msg': '仅管理员可变更权限'}), 403

    data = request.get_json(force=True, silent=True) or {}
    new_role = data.get('role')
    if new_role not in VALID_ROLES:
        return jsonify({'code': 400, 'msg': f'无效的 role，可选值：{", ".join(sorted(VALID_ROLES))}'}), 400

    target = db.get_user_by_id(user_id)
    if not target:
        return jsonify({'code': 404, 'msg': '用户不存在'}), 404

    updated = db.update_user_role(viewer.user_id, user_id, new_role)
    if not updated:
        return jsonify({'code': 500, 'msg': '更新失败'}), 500
    return jsonify({
        'code': 200,
        'msg': 'success',
        'data': updated.to_public(),
    })


# ========================== 题目 & 判题 API ==========================

@app.route('/api/problem/<problem_id>')
def get_problem_compat(problem_id):
    p = db.get_problem(problem_id)
    if not p:
        return jsonify({'code': 404, 'msg': '题目不存在', 'data': None}), 404
    return jsonify(p)


# ========= Step 1 标准题目管理 API（与文档对齐）=========

@app.route('/api/problems/', methods=['GET'])
@app.route('/api/problems', methods=['GET'])
def api_problems_list():
    viewer = current_user()
    if not viewer:
        return jsonify({'code': 401, 'msg': '请先登录', 'data': None}), 401
    brief = db.list_problems_brief()
    return jsonify({'code': 200, 'msg': 'success', 'data': brief})


@app.route('/api/problems/', methods=['POST'])
@app.route('/api/problems', methods=['POST'])
def api_problems_create():
    viewer = current_user()
    if not viewer:
        return jsonify({'code': 401, 'msg': '请先登录', 'data': None}), 401
    data = request.get_json(force=True, silent=True) or {}
    pid = (data.get('id') or '').strip()
    title = (data.get('title') or '').strip()
    required = ['id', 'title', 'description', 'input_description',
                'output_description', 'samples', 'constraints', 'testcases']
    missing = [k for k in required if k not in data or data.get(k) is None
               or (isinstance(data.get(k), str) and not (data.get(k) or '').strip()
                   and k in ('id', 'title'))]
    if not pid:
        return jsonify({'code': 400, 'msg': '缺少必填字段：id'}), 400
    if not title:
        return jsonify({'code': 400, 'msg': '缺少必填字段：title'}), 400
    samples = data.get('samples') or []
    testcases = data.get('testcases') or []
    if not isinstance(samples, list):
        return jsonify({'code': 400, 'msg': 'samples 必须为数组'}), 400
    if not isinstance(testcases, list):
        return jsonify({'code': 400, 'msg': 'testcases 必须为数组'}), 400
    tags = data.get('tags') or []
    if not isinstance(tags, list):
        return jsonify({'code': 400, 'msg': 'tags 必须为数组'}), 400
    created = db.create_problem(data)
    if not created:
        if db.get_problem(pid):
            return jsonify({'code': 409, 'msg': f'题目 ID [{pid}] 已存在'}), 409
        return jsonify({'code': 400, 'msg': '创建题目失败，请检查字段'}), 400
    return jsonify({'code': 200, 'msg': '创建成功', 'data': {'id': created['id']}})


@app.route('/api/problems/<problem_id>', methods=['GET'])
def api_problems_get(problem_id):
    viewer = current_user()
    if not viewer:
        return jsonify({'code': 401, 'msg': '请先登录', 'data': None}), 401
    p = db.get_problem(problem_id)
    if not p:
        return jsonify({'code': 404, 'msg': '题目不存在', 'data': None}), 404
    return jsonify({'code': 200, 'msg': 'success', 'data': p})


@app.route('/api/problems/<problem_id>', methods=['PUT'])
def api_problems_update(problem_id):
    viewer = current_user()
    if not viewer:
        return jsonify({'code': 401, 'msg': '请先登录', 'data': None}), 401
    data = request.get_json(force=True, silent=True) or {}
    body_id = (data.get('id') or '').strip()
    if body_id and body_id != problem_id:
        return jsonify({'code': 400,
                        'msg': f'请求体 id[{body_id}] 与路径 id[{problem_id}] 不一致'}), 400
    if not db.get_problem(problem_id):
        return jsonify({'code': 404, 'msg': '题目不存在', 'data': None}), 404
    samples = data.get('samples')
    if samples is not None and not isinstance(samples, list):
        return jsonify({'code': 400, 'msg': 'samples 必须为数组'}), 400
    testcases = data.get('testcases')
    if testcases is not None and not isinstance(testcases, list):
        return jsonify({'code': 400, 'msg': 'testcases 必须为数组'}), 400
    tags = data.get('tags')
    if tags is not None and not isinstance(tags, list):
        return jsonify({'code': 400, 'msg': 'tags 必须为数组'}), 400
    updated = db.update_problem(problem_id, data)
    if not updated:
        return jsonify({'code': 500, 'msg': '更新失败'}), 500
    return jsonify({'code': 200, 'msg': '更新成功', 'data': {'id': updated['id']}})


@app.route('/api/problems/<problem_id>', methods=['DELETE'])
@require_login(allow_admin_only=True)
def api_problems_delete(viewer, problem_id):
    if not db.get_problem(problem_id):
        return jsonify({'code': 404, 'msg': '题目不存在', 'data': None}), 404
    ok = db.delete_problem(problem_id)
    if not ok:
        return jsonify({'code': 500, 'msg': '删除失败'}), 500
    return jsonify({'code': 200, 'msg': '删除成功', 'data': {'id': problem_id}})


@app.route('/api/judge', methods=['POST'])
def api_judge():
    user = current_user()
    if not user:
        return jsonify({'code': 401, 'msg': '请先登录后再提交判题', 'data': None}), 401

    data = request.get_json(force=True)
    code = data.get('code', '')
    problem_id = data.get('problem_id', '')
    custom_cases = data.get('custom_cases', [])
    use_samples = data.get('use_samples', True)
    sample_overrides = data.get('_sample_overrides') or []
    time_limit = float(data.get('time_limit', 1.0))
    memory_limit = int(data.get('memory_limit', 128))
    compare_mode = data.get('compare_mode', 'exact')

    test_cases = []
    cid = 0

    problem = db.get_problem(problem_id)

    if use_samples and problem:
        samples = problem['samples']
        if sample_overrides and len(sample_overrides) == len(samples):
            samples = sample_overrides
        for s in samples:
            inp = s.get('input', '')
            if not inp.endswith('\n'):
                inp += '\n'
            out = s.get('output', '')
            if not out.endswith('\n'):
                out += '\n'
            test_cases.append(TestCase(
                input_data=inp,
                expected_output=out,
                case_id=cid,
                is_sample=True,
            ))
            cid += 1

    for cc in custom_cases:
        inp = cc.get('input', '')
        if not inp.endswith('\n'):
            inp += '\n'
        out = cc.get('output', '')
        if not out.endswith('\n'):
            out += '\n'
        test_cases.append(TestCase(
            input_data=inp,
            expected_output=out,
            case_id=cid,
            is_sample=False,
        ))
        cid += 1

    if not test_cases:
        return jsonify({'code': 400,
                        'msg': '没有可用的测试用例，请至少勾选样例或添加自定义用例。',
                        'data': None}), 400

    judger = Judger(
        default_time_limit=time_limit,
        default_memory_limit=memory_limit,
        compare_mode=compare_mode,
    )
    result = judger.judge(code, test_cases, Language.PYTHON)
    serialized = serialize_result(result)
    serialized['cases'] = serialized['case_results']

    total = result.total_cases
    passed = result.passed_cases
    all_pass = total > 0 and passed == total
    db.increment_submit(user.user_id, all_pass)

    db.record_submission(
        user_id=user.user_id,
        problem_id=problem_id,
        status=result.status.value,
        code=code,
        total_time_ms=result.total_time * 1000,
        max_memory_mb=result.max_memory,
        pass_cases=passed,
        total_cases=total,
        case_results=json.dumps(serialized['case_results'], ensure_ascii=False),
    )

    return jsonify({'code': 200, 'msg': 'success', 'data': serialized})


if __name__ == '__main__':
    print('=' * 60)
    print('  OJ 调试平台 Web 服务启动中...')
    print('  访问地址: http://127.0.0.1:5000/')
    print('  初始管理员: admin / ' + INITIAL_ADMIN_PASSWORD)
    print('=' * 60)
    app.run(host='127.0.0.1', port=5000, debug=False)
