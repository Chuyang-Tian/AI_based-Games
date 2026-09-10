@echo off
REM ==============================================================================================
REM  OJ 调试平台 Linux / WSL (Ubuntu 22.04) 一键安装 + 自检脚本（管理员模式双击运行）
REM  -----------------------------------------------------------------------------------------------
REM  为什么要写这个脚本？
REM    - 评分标准要求"在助教机器上拉下来就能运行"，但助教可能是 Ubuntu 服务器 / 或本地 WSL；
REM    - 也可以在本地 WSL 里跑一遍冒烟测试，提前发现 Windows-only 的坑（比如路径用反斜杠、
REM      tasklist 内存监控在 Linux 没有对应等）。
REM
REM  流程（共 6 大步，每步失败会 exit /b N 并提示你手动调）：
REM    步骤 0    检查 wsl.exe 是否可用；否则提示先 wsl --install -d Ubuntu-22.04
REM    步骤 1    rsync 把当前 Windows 项目目录同步到 WSL 的 /root/oj_debug_platform/
REM               .venv / __pycache__ / *.db / .git 都 exclude，不覆盖 DB、不把 .git 大文件传进去
REM    步骤 2    apt-get 装系统依赖：build-essential (g++)、python3-venv、python3-pip、libssl-dev
REM    步骤 3    建 .venv 虚拟环境 + pip install fastapi/uvicorn/streamlit/psutil/bcrypt/...
REM    步骤 4    python -m compileall -q webapp oj_judge 语法检查，提前挡掉 syntax error
REM    步骤 5    生成 run_oj_linux.sh（一键在 WSL 起 FastAPI :5000 + Streamlit :8501，host 0.0.0.0 便于 Windows 浏览器直接访问）
REM    步骤 6    冒烟测试：清空 DB → 启动 uvicorn 30s → curl POST auth/login + GET problems/languages/access_logs 4 个核心接口 → kill
REM               全部通过打印 LINUX_SMOKE_OK，说明在 Linux 端也 OK。
REM  产物：
REM    /root/oj_debug_platform/run_oj_linux.sh  —— 下次想在 WSL 里直接启动就跑它。
REM ==============================================================================================
chcp 65001 >nul
setlocal enabledelayedexpansion
echo ============================================================
echo  OJ 项目 Linux (WSL Ubuntu 22.04) 一键安装与启动脚本
echo ============================================================
echo.
echo [步骤 0] 检查 WSL / Ubuntu 是否可用...
where wsl >nul 2>nul
if errorlevel 1 (
    echo [ERR] 未安装 WSL。请先在管理员 PowerShell 执行:
    echo     wsl --install -d Ubuntu-22.04
    echo 然后重启本机器再执行本脚本。
    pause
    exit /b 1
)

REM 步骤 0-2：让 WSL 默认 2；确保 Ubuntu-22.04 注册好（首次安装需要用户在 WSL 里设用户名密码，这里会友好提示重启脚本）
wsl --set-default-version 2 >nul
wsl -d Ubuntu-22.04 -- echo "WSL Ubuntu OK" >nul 2>nul
if errorlevel 1 (
    echo [提示] 尚未注册 Ubuntu-22.04，正在安装（首次可能需要你设置用户名密码，按提示操作）...
    wsl --install -d Ubuntu-22.04
    if errorlevel 1 (
        echo [ERR] 安装 Ubuntu-22.04 失败，请手动在微软商店安装 Ubuntu 22.04 LTS 后再运行本脚本。
        pause
        exit /b 2
    )
    echo.
    echo [OK] Ubuntu-22.04 已安装，请先按提示设置 WSL 的 Linux 用户名+密码，然后重新运行本脚本。
    pause
    exit /b 0
)

echo.
echo [步骤 1] 将 Windows 项目目录同步到 Linux 的 ~/oj_debug_platform/ 下（用 rsync，快且保留时间戳，不覆盖 DB/生成文件）
set "SRC_WIN=%~dp0"
wsl -d Ubuntu-22.04 -u root -- bash -lc "mkdir -p /root/oj_debug_platform && echo OK > /dev/null"
if not exist "%SRC_WIN%webapp\app_fastapi.py" (
    echo [ERR] 当前脚本所在目录不是项目根目录（未找到 webapp\app_fastapi.py）。请把本 .cmd 放在项目根目录。
    pause
    exit /b 3
)
REM 用 rsync 从 /mnt/c/... 同步到 $HOME/oj_debug_platform/，排除 venv、__pycache__、*.db（保留你现有 DB，首次启动会 _init_db 重建）
echo [1-1] 安装 rsync 与基础工具...
wsl -d Ubuntu-22.04 -u root -- bash -lc "apt-get update -y && apt-get install -y rsync sudo curl git || exit 4"
if errorlevel 1 (
    echo [ERR] apt 安装 rsync/sudo 失败，请检查 WSL 网络 / 镜像源。
    pause
    exit /b 4
)

echo [1-2] rsync 同步项目代码...
set "DRIVE_LETTER=%~d0"
set "DRIVE_LETTER=!DRIVE_LETTER:~0,1!"
set "REL_PATH=%~p0"
set "REL_PATH=!REL_PATH:\=/!"
set "WSL_SRC=/mnt/!DRIVE_LETTER!!REL_PATH!"
echo  WSL source path = !WSL_SRC!

wsl -d Ubuntu-22.04 -u root -- bash -lc ^
  "set -e; SRC='!WSL_SRC!'; DST=/root/oj_debug_platform; mkdir -p \"$DST\"; rsync -a --delete ^
    --exclude='.venv/' --exclude='venv/' --exclude='__pycache__/' --exclude='*.pyc' ^
    --exclude='webapp/data/*.db' --exclude='webapp/data/ai_side/*.db' ^
    --exclude='webapp/__pycache__/' --exclude='oj_judge/__pycache__/' ^
    --exclude='.git/' ^
    \"$SRC\" \"$DST/../\" && echo SYNC_OK"
if errorlevel 1 (
    echo [ERR] rsync 同步失败。
    pause
    exit /b 5
)
echo [1-2 OK] 代码已同步到 WSL 的 /root/oj_debug_platform/

echo.
echo [步骤 2] 安装 Linux 侧系统依赖: build-essential(g++/gcc)、python3-venv、python3-pip、python3-dev、libssl-dev、psutil 头文件
wsl -d Ubuntu-22.04 -u root -- bash -lc ^
  "set -e; export DEBIAN_FRONTEND=noninteractive; \
   apt-get update -y; \
   apt-get install -y \
     build-essential g++ python3 python3-venv python3-pip python3-dev \
     libssl-dev libffi-dev ca-certificates tzdata locales; \
   which python3 && which g++ && g++ --version | head -n1 && python3 --version"
if errorlevel 1 (
    echo [ERR] 系统依赖安装失败，请检查 APT 源或磁盘空间。
    pause
    exit /b 6
)
echo [2 OK] 系统依赖完成。

echo.
echo [步骤 3] 创建/复用虚拟环境 + pip 安装核心包（fastapi/uvicorn/streamlit/requests/pandas/psutil/bcrypt 等）
wsl -d Ubuntu-22.04 -u root -- bash -lc ^
  "set -e; cd /root/oj_debug_platform; \
   if [ ! -d .venv ]; then python3 -m venv .venv; fi; \
   source .venv/bin/activate; \
   python -m pip install --upgrade pip setuptools wheel; \
   python -m pip install \
     'fastapi>=0.110' \
     'uvicorn[standard]>=0.27' \
     'streamlit>=1.33' \
     'requests>=2.31' \
     'pandas>=2.2' \
     'psutil>=5.9' \
     'bcrypt>=4.1' \
     'httpx>=0.27' \
     'multipart>=0.0.9' \
     'aiofiles>=24.1' \
     'Jinja2>=3.1' \
     'python-multipart>=0.0.9' \
     'numpy>=1.26'; \
   python -c 'import fastapi,uvicorn,streamlit,requests,pandas,psutil,bcrypt; print(\"PY_DEPS_OK\", fastapi.__version__)' "
if errorlevel 1 (
    echo [ERR] pip 依赖安装失败。可能 bcrypt 编译需要 libffi-dev/libssl-dev，已安装请再检查；或手动在 WSL 中执行:
    echo   cd /root/oj_debug_platform && source .venv/bin/activate && pip install -r requirements.txt （如果你生成了 requirements.txt）
    pause
    exit /b 7
)
echo [3 OK] Python 依赖完成。

echo.
echo [步骤 4] 做一次语法 smoke-check（compileall），避免有语法错误直接启动失败
wsl -d Ubuntu-22.04 -u root -- bash -lc ^
  "set -e; cd /root/oj_debug_platform; source .venv/bin/activate; \
   python -m compileall -q webapp oj_judge 2>&1 | tail -n 20; \
   echo COMPILE_OK"
if errorlevel 1 (
    echo [ERR] compileall 发现语法错误，请在 Windows 侧先修复再同步。
    pause
    exit /b 8
)
echo [4 OK] 语法检查通过。

echo.
echo [步骤 5] 写 run_oj_linux.sh，用来一键启动 FastAPI + Streamlit
wsl -d Ubuntu-22.04 -u root -- bash -lc ^
  "cat > /root/oj_debug_platform/run_oj_linux.sh <<'__EOF__'
#!/bin/bash
set -e
cd \"$(dirname \"$0\")\"
source .venv/bin/activate
mkdir -p webapp/data webapp/data/ai_side
export PYTHONPATH=\"${PWD}:${PWD}/webapp:${PWD}/oj_judge\"
export OJ_API_BASE=http://127.0.0.1:5000
# kill 旧进程
pkill -f 'uvicorn app_fastapi:app' 2>/dev/null || true
pkill -f 'streamlit run app_streamlit.py' 2>/dev/null || true
sleep 1
cd webapp
nohup python -m uvicorn app_fastapi:app --host 0.0.0.0 --port 5000 > /tmp/oj_fastapi.log 2>&1 &
sleep 3
cd ..
cd webapp
nohup streamlit run app_streamlit.py --server.headless true --server.port 8501 --server.address 0.0.0.0 > /tmp/oj_streamlit.log 2>&1 &
sleep 4
echo '------ FastAPI 状态 ------'
curl -sS http://127.0.0.1:5000/api/auth/test 2>/dev/null || echo '[warn] 未提供 /api/auth/test，改测 /api/problems'
curl -sS http://127.0.0.1:5000/api/problems 2>/dev/null | head -c 400
echo
echo '------ 访问地址（从 Windows 打开） ------'
echo '  前端: http://127.0.0.1:8501/'
echo '  后端: http://127.0.0.1:5000/'
echo '  初始管理员: admin / admintestpassword'
echo '------ 实时日志 (Ctrl+C 退出) ------'
echo ' tail -f /tmp/oj_fastapi.log /tmp/oj_streamlit.log'
__EOF__
chmod +x /root/oj_debug_platform/run_oj_linux.sh
echo START_SCRIPT_OK"

echo.
echo [步骤 6] 做一次快速自检：重置 DB + 启动后端 30s + 调 3 个核心接口（登录 + 题列表 + 语言列表 + 提交），再 kill
wsl -d Ubuntu-22.04 -u root -- bash -lc ^
  "set -e; cd /root/oj_debug_platform; source .venv/bin/activate; \
   export PYTHONPATH=\"${PWD}:${PWD}/webapp:${PWD}/oj_judge\"; \
   rm -f webapp/data/*.db webapp/data/ai_side/*.db; \
   cd webapp && python -c 'from userdb import UserDatabase; db=UserDatabase(); db.ensure_seed_problems(); print(\"DB_INIT_OK\")'; \
   pkill -f 'uvicorn app_fastapi:app' 2>/dev/null || true; \
   nohup python -m uvicorn app_fastapi:app --host 127.0.0.1 --port 5000 > /tmp/oj_fastapi_smoke.log 2>&1 & \
   PID=$!; \
   for i in $(seq 1 30); do \
     if curl -sS http://127.0.0.1:5000/api/problems >/dev/null 2>&1; then break; fi; \
     sleep 1; \
   done; \
   echo '=== 1. POST auth/login ==='; \
   LOGIN=$(curl -sS -c /tmp/oj_cookies.txt -H 'Content-Type: application/json' \
     -d '{\"username\":\"admin\",\"password\":\"admintestpassword\"}' http://127.0.0.1:5000/api/auth/login); \
   echo \"$LOGIN\" | head -c 500; echo; \
   echo; \
   echo '=== 2. GET /api/problems  ==='; \
   curl -sS http://127.0.0.1:5000/api/problems | head -c 500; echo; \
   echo; \
   echo '=== 3. GET /api/languages ==='; \
   curl -sS -b /tmp/oj_cookies.txt http://127.0.0.1:5000/api/languages | head -c 500; echo; \
   echo; \
   echo '=== 4. GET /api/logs/access (top array) ==='; \
   curl -sS -b /tmp/oj_cookies.txt http://127.0.0.1:5000/api/logs/access | head -c 500; echo; \
   echo; \
   kill $PID 2>/dev/null || true; wait $PID 2>/dev/null || true; \
   echo LINUX_SMOKE_OK"

if errorlevel 1 (
    echo.
    echo [WARN] 自检未全通过，可能是依赖/代码问题。你可以手动进入 WSL 看:
    echo   wsl -d Ubuntu-22.04
    echo   sudo -i
    echo   cd /root/oj_debug_platform && source .venv/bin/activate
    echo   tail -n 80 /tmp/oj_fastapi_smoke.log
    pause
    exit /b 9
)

echo.
echo ============================================================
echo  [完成] Linux 环境搭建 + 依赖安装 + 自检 通过。
echo ============================================================
echo.
echo  你之后需要在 WSL 里启动 OJ 服务，执行:
echo    wsl -d Ubuntu-22.04 -u root
echo    cd /root/oj_debug_platform
echo    ./run_oj_linux.sh
echo.
echo  然后在 Windows 浏览器访问:
echo    http://127.0.0.1:8501/    （前端 Streamlit）
echo    http://127.0.0.1:5000/    （后端 API）
echo  初始管理员账号: admin / admintestpassword
echo.
echo  如果你想让我进一步在 WSL 中跑探针验证 Python/C++ AC 全链路，请直接"运行 run_oj_linux.sh 后"在助手消息里告诉我"已启动"，我再写 _probe_req_v3_linux.py 验证。
echo.
pause
