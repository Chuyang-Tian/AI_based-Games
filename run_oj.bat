@echo off
REM ==============================================================================================
REM  OJ 调试平台 Windows 一键启动脚本（双击即可）
REM  -----------------------------------------------------------------------------------------------
REM  作用：
REM    1. chcp 65001              : 控制台切 UTF-8，避免显示中文乱码；
REM    2. 清理端口占用（5000/8501）: 前一次 run 可能没正常关，会导致端口被占用、启动失败，
REM                                   用 PowerShell Get-NetTCPConnection 找到对应 PID 并 Stop-Process 杀；
REM    3. 拉起两个独立 cmd 窗口（不用 start /B，这样关窗口就是停服务，交付时直观）：
REM         ① OJ FastAPI    : webapp/app_fastapi.py 作为 ASGI 入口，uvicorn --port 5000 --reload
REM                           所有 REST API（/api/*）都在这个进程；
REM         ② OJ Streamlit  : webapp/app_streamlit.py 作为多页 UI 入口，streamlit run --server.port 8501
REM                           设置 OJ_API_BASE=http://127.0.0.1:5000 告诉 common.api 往哪转发；
REM    4. pause 让用户看到"已启动"信息，不立刻关窗口。
REM
REM  端口说明：
REM    :5000 FastAPI（后端）    -> 直接浏览器访问可以看 /docs Swagger UI
REM    :8501 Streamlit（前端）  -> 用户日常登录 / 做题 / 看提交
REM
REM  默认管理员账号： admin / admintestpassword  （userdb.INITIAL_ADMIN_* 控制）
REM ==============================================================================================
chcp 65001 >nul
set "ROOT=%~dp0"
set "WEBAPP=%ROOT%webapp"
title OJ 调试平台 - 一键启动

echo ============================================================
echo   OJ 调试平台启动中...
echo   FastAPI API:   http://127.0.0.1:5000/
echo   Streamlit UI:  http://127.0.0.1:8501/
echo   初始管理员: admin / admintestpassword
echo ============================================================

echo 正在清理旧的 5000 / 8501 端口占用...
for %%P in (5000 8501) do (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-NetTCPConnection -LocalPort %%P -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { try { Stop-Process -Id $_ -Force -ErrorAction Stop } catch {} }" >nul 2>nul
)

REM 两个独立窗口启动，便于查看日志、关闭窗口即停止
start "OJ FastAPI" cmd /k "cd /d ""%WEBAPP%"" && python -m uvicorn app_fastapi:app --host 127.0.0.1 --port 5000 --reload"
start "OJ Streamlit" cmd /k "cd /d ""%WEBAPP%"" && set OJ_API_BASE=http://127.0.0.1:5000 && streamlit run app_streamlit.py --server.port 8501 --server.headless true"

echo 已分别打开 FastAPI 与 Streamlit 窗口。
echo 关闭对应窗口即可停止服务。
pause
