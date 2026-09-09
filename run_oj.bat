@echo off
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

start "OJ FastAPI" cmd /k "cd /d ""%WEBAPP%"" && python app_fastapi.py"
start "OJ Streamlit" cmd /k "cd /d ""%WEBAPP%"" && set OJ_API_BASE=http://127.0.0.1:5000 && streamlit run app_streamlit.py --server.port 8501 --server.headless true"

echo 已分别打开 FastAPI 与 Streamlit 窗口。
echo 关闭对应窗口即可停止服务。
pause
