# 知行书院 · 智慧图书馆全栈一键启动脚本 (PowerShell)
$root = $PSScriptRoot
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  知行书院 · 智慧图书馆全栈一键启动" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

Write-Host "`n[1/2] 正在启动后端 Django 服务 (http://127.0.0.1:8000)..." -ForegroundColor Yellow
$backendPython = if (Test-Path "$root\backend\.venv\Scripts\python.exe") { "$root\backend\.venv\Scripts\python.exe" } else { "python" }
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\backend'; & '$backendPython' manage.py runserver 0.0.0.0:8000"

Start-Sleep -Seconds 2

Write-Host "[2/2] 正在启动前端开发服务并自动弹开浏览器 (http://localhost:5173)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root'; npm run dev -- --open"

Write-Host "`n前后端已分别在新终端窗口中启动，正在为您打开浏览器！" -ForegroundColor Cyan
