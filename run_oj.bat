@echo off
chcp 65001 >nul
title OJ 调试平台 - FastAPI 启动
cd /d "%~dp0webapp"
echo ============================================================
echo   OJ 调试平台 Web 服务启动中...
echo   访问地址: http://127.0.0.1:5000/
echo   初始管理员: admin / admintestpassword
echo   (按 Ctrl+C 停止服务)
echo ============================================================
python app_fastapi.py
pause
