# -*- coding: utf-8 -*-
"""
============================================================
 OJ V6 冒烟测试脚本（交付自查用）
============================================================
 功能说明：
   一次性验证「作业/考试卡片化 + 班级成员可操作化」所有后端接口。
   共 7 条断言，覆盖 管理员登录 / 4 大列表接口 / 学生权限隔离 。

 运行前提（先在 webapp 目录启动服务器）：
   > cd webapp && python app_fastapi.py

 运行方法（新开一个 cmd/PowerShell）：
   > cd 大作业2-OJ调试平台 && python smoke_tests_v6.py

 预期结果：
   7/7 ALL PASS，退出码 0；若任何一条失败 → exit 1 + 打印 FAIL 清单
============================================================
"""
import sys
import io
import json
import random
import string
import urllib.request
import urllib.error

# ===== 工具层：Windows 中文 GBK 控制台强制 UTF-8，避免乱码 =====
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = 'http://127.0.0.1:5000'
LIST_PASS = []
LIST_FAIL = []


def http_request(path, method='GET', body=None, cookie=None):
    """统一 HTTP 请求封装：返回 (http_code, json_body, set_cookie_str)"""
    url = BASE_URL + path
    payload = json.dumps(body).encode('utf-8') if body is not None else None
    headers = {'Content-Type': 'application/json'}
    if cookie:
        headers['Cookie'] = cookie
    req = urllib.request.Request(url, data=payload, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode('utf-8')
            return resp.status, json.loads(raw), resp.headers.get('Set-Cookie', '')
    except urllib.error.HTTPError as e:
        # 非 2xx 的响应也需要读 body（比如 401/403/404 的错误信息）
        try:
            raw = e.read().decode('utf-8')
        except Exception:
            raw = '{}'
        try:
            js = json.loads(raw)
        except Exception:
            js = {'msg': raw}
        return e.code, js, ''
    except Exception as e:
        return -1, {'msg': str(e)}, ''


def assert_check(name, ok, detail=''):
    """断言输出并记录 PASS/FAIL（用 LIST 保留历史，exit 时汇总）"""
    if ok:
        LIST_PASS.append(name)
        print(f'[PASS] {name} {detail}')
    else:
        LIST_FAIL.append(name)
        print(f'[FAIL] {name} {detail}')


def extract_session_cookie(set_cookie_header):
    """从 Set-Cookie 头中抽取 oj_session_id=xxx 片段；会话全程复用"""
    if not set_cookie_header:
        return None
    for segment in set_cookie_header.split(';'):
        segment = segment.strip()
        if segment.startswith('oj_session_id='):
            return segment
    return None


# ============================================================
# 冒烟阶段 1：管理员登录（拿到后续 4 个接口的鉴权 cookie）
# ============================================================
print('=== V6 冒烟开始（服务器需已监听 http://127.0.0.1:5000） ===')
print(f'目标后端：{BASE_URL}\n')

code, data, cookie_raw = http_request(
    '/api/auth/login', 'POST',
    {'username': 'admin', 'password': 'admintestpassword'}
)
ADMIN_COOKIE = extract_session_cookie(cookie_raw)
assert_check(
    't1_admin_login',
    code == 200 and data.get('code') == 200 and ADMIN_COOKIE is not None,
    f'http={code} api={data.get("code")} has_session={bool(ADMIN_COOKIE)}'
)
print()


# ============================================================
# 冒烟阶段 2：4 大列表接口（作业/考试/班级/班级成员）
# ============================================================
# --- 2a 作业列表（前端作业卡片页数据来源）
code, data, _ = http_request('/api/assignments', cookie=ADMIN_COOKIE)
assert_check(
    't2_assignments_200',
    code == 200 and data.get('code') == 200 and isinstance(data.get('data'), list),
    f'http={code} api={data.get("code")} 数量={len(data.get("data", []) or [])}'
)

# --- 2b 考试列表（前端考试卡片页数据来源）
code, data, _ = http_request('/api/exams', cookie=ADMIN_COOKIE)
assert_check(
    't3_exams_200',
    code == 200 and data.get('code') == 200 and isinstance(data.get('data'), list),
    f'http={code} api={data.get("code")} 数量={len(data.get("data", []) or [])}'
)

# --- 2c 班级列表（顺便取第一个班级 ID 给 t5 成员接口用）
code, data, _ = http_request('/api/classes', cookie=ADMIN_COOKIE)
CLASS_LIST = data.get('data') or []
FIRST_CLASS_ID = None
if isinstance(CLASS_LIST, list) and len(CLASS_LIST) > 0:
    FIRST_CLASS_ID = CLASS_LIST[0].get('class_id') or CLASS_LIST[0].get('id')
assert_check(
    't4_classes_200',
    code == 200 and data.get('code') == 200 and isinstance(CLASS_LIST, list),
    f'http={code} api={data.get("code")} 数量={len(CLASS_LIST)} 首个班级ID={FIRST_CLASS_ID}'
)
print()

# --- 2d 班级成员列表（本轮核心修复：BUG A 原来缺这个 GET 路由！）
if FIRST_CLASS_ID is not None:
    code, data, _ = http_request(f'/api/classes/{FIRST_CLASS_ID}/members', cookie=ADMIN_COOKIE)
    members = data.get('data')
    assert_check(
        't5_class_members_200_admin',
        code == 200 and data.get('code') == 200 and isinstance(members, list),
        f'http={code} api={data.get("code")} 成员数={len(members) if isinstance(members, list) else "N/A"}'
    )
else:
    assert_check(
        't5_class_members_200_admin', False,
        '无法测试：数据库暂无班级（请先通过 UI 新建 1 个班级再跑本脚本）'
    )
print()


# ============================================================
# 冒烟阶段 3：学生注册/登录（用于权限隔离断言 t7）
# ============================================================
STUDENT_COOKIE = None
BASE_STU_NAME = 'stu_v6_smoke'
BASE_STU_PWD = 'test123456'

# 方案 A：尝试直接注册新学生
code, data, _ = http_request(
    '/api/auth/register', 'POST',
    {'username': BASE_STU_NAME, 'password': BASE_STU_PWD, 'role': 'student'}
)
if code == 200 and data.get('code') == 200:
    print(f'[INFO] 新学生注册成功：用户名={BASE_STU_NAME}')
    c2, d2, sc2 = http_request(
        '/api/auth/login', 'POST',
        {'username': BASE_STU_NAME, 'password': BASE_STU_PWD}
    )
    STUDENT_COOKIE = extract_session_cookie(sc2)
    assert_check(
        't6_student_login', c2 == 200 and d2.get('code') == 200 and bool(STUDENT_COOKIE),
        f'http={c2} api={d2.get("code")}'
    )
elif data.get('code') == 409:
    # 方案 B：用户名已存在（多轮跑过）→ 直接登录
    print(f'[INFO] 学生 {BASE_STU_NAME} 已存在，直接复用登录')
    c2, d2, sc2 = http_request(
        '/api/auth/login', 'POST',
        {'username': BASE_STU_NAME, 'password': BASE_STU_PWD}
    )
    if c2 == 200 and d2.get('code') == 200:
        STUDENT_COOKIE = extract_session_cookie(sc2)
        assert_check('t6_student_login', True, f'(已有账号复用) http={c2} api={d2.get("code")}')
    else:
        # 方案 C：旧密码不对（脏数据）→ 换随机后缀全新注册
        print('[WARN] 旧学生账号密码错误，启用随机后缀注册新用户')
        suffix = ''.join(random.choices(string.ascii_lowercase, k=4))
        new_name = f'stu_v6_{suffix}'
        http_request('/api/auth/register', 'POST',
                     {'username': new_name, 'password': 'p123456', 'role': 'student'})
        c4, d4, sc4 = http_request('/api/auth/login', 'POST',
                                   {'username': new_name, 'password': 'p123456'})
        STUDENT_COOKIE = extract_session_cookie(sc4)
        assert_check(
            't6_student_login', c4 == 200 and d4.get('code') == 200 and bool(STUDENT_COOKIE),
            f'新用户={new_name} http={c4} api={d4.get("code")}'
        )
else:
    assert_check(
        't6_student_login', False,
        f'注册/登录失败 http={code} api={data.get("code")} msg={data.get("msg")}'
    )
print()


# ============================================================
# 冒烟阶段 4：学生越权访问班级成员 → 必须 403（权限底线）
# ============================================================
if FIRST_CLASS_ID is not None and STUDENT_COOKIE:
    code, data, _ = http_request(
        f'/api/classes/{FIRST_CLASS_ID}/members', cookie=STUDENT_COOKIE
    )
    assert_check(
        't7_student_403_on_members',
        (code == 403 or data.get('code') == 403),
        f'http={code} api={data.get("code")} 后端返回={data.get("msg", "")}'
    )
else:
    assert_check(
        't7_student_403_on_members', False,
        '无法测试：前置 t4（班级列表）或 t6（学生登录）未通过'
    )
print()


# ============================================================
# 汇总：7/7 全过 → exit 0，否则 exit 1
# ============================================================
total = len(LIST_PASS) + len(LIST_FAIL)
print(f'=== 汇总：{len(LIST_PASS)}/{total} 条通过 ===')
if LIST_FAIL:
    print('失败清单：', LIST_FAIL)
    sys.exit(1)
else:
    print('🎉 全部 7 条冒烟断言通过，V6 交付合格！')
    sys.exit(0)
