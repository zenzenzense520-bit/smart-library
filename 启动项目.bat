@echo off
chcp 65001 >nul
title 知行书院 · 智慧图书馆一键启动器
echo ===================================================
echo   知行书院 · 智慧图书馆全栈一键启动
echo ===================================================
echo.
echo [1/2] 正在启动后端服务 (Django http://127.0.0.1:8000)...
start "智慧图书馆 - 后端 Django" cmd /k "cd /d "%~dp0backend" && (if exist .venv\Scripts\python.exe (.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000) else (python manage.py runserver 0.0.0.0:8000))"

echo [2/2] 正在启动前端界面并自动打开浏览器 (Vite http://localhost:5173)...
timeout /t 2 /nobreak >nul
start "智慧图书馆 - 前端 Vite" cmd /k "cd /d "%~dp0" && npm run dev -- --open"

echo.
echo ===================================================
echo   前后端服务已启动！
echo   前端开发地址: http://localhost:5173
echo   后端 API 地址: http://localhost:8000/api
echo   演示学生账户: student@zhixing.local / Student123!
echo   演示管理员账户: admin@zhixing.local / Admin123!
echo ===================================================
echo.
pause
