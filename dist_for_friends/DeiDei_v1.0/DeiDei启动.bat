@echo off
chcp 65001 >nul
title DeiDei 叠叠对战 一键启动
cd /d "%~dp0"

echo ========================================================
echo   DeiDei 叠叠对战 一键启动（朋友版）
echo ========================================================
echo.
echo [1/2] 检查并安装依赖（第一次启动会稍慢，之后秒跳过）
where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo ❌ 没检测到 Python！
    echo 请先去 https://www.python.org/downloads/ 下载 Python 3.10 或以上，安装时勾 "Add Python to PATH"
    echo 安装完成后再双击本文件即可~
    echo.
    pause
    exit /b 1
)
python -c "import numpy, torch, stable_baselines3" >nul 2>nul
if errorlevel 1 (
    echo     首次启动，正在安装依赖（numpy / torch / stable-baselines3 / gymnasium ...）...
    echo     （约 1~3 分钟，只装这一次~）
    python -m pip install --upgrade pip
    python -m pip install -r requirements_rl.txt
    if errorlevel 1 (
        echo.
        echo ❌ 依赖安装失败（大概率是网络问题），手动执行：
        echo    python -m pip install -r requirements_rl.txt
        pause
        exit /b 1
    )
) else (
    echo     依赖已就绪，跳过安装。
)
echo.
echo [2/2] 启动 DeiDei 叠叠对战 GUI...
echo.
python gui_deidei.py
if errorlevel 1 (
    echo.
    echo 启动失败？把上面的报错截图发给我~
    pause
)
