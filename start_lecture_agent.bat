@echo off
title FinTech AI Assistant
echo Starting Lecture Note Daemon...


call C:\miniconda3\condabin\conda.bat activate lecture_agent

if errorlevel 1 (
    echo [Error] Failed to activate conda environment!
    echo Please check your conda path in the bat file.
    pause
    exit /b
)

:: 运行 Python 脚本
python lecture_agent_daemon.py

:: 如果程序崩溃，暂停显示错误信息
pause