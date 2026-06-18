@echo off
cd /d E:\OpenClaw\backend
echo.
echo ========================================
echo   量化交易系统 v4.0 启动脚本
echo ========================================
echo.

:: 清理端口
echo [1/3] 清理端口 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1
timeout /t 1 /nobreak >nul

:: 启动后端
echo [2/3] 启动后端服务器...
start /B python -m uvicorn main:app --host 0.0.0.0 --port 8000

:: 等待启动
echo [3/3] 等待服务器启动...
timeout /t 3 /nobreak >nul

:: 验证
curl -s http://localhost:8000/api/health >nul 2>&1
if %errorlevel%==0 (
    echo.
    echo ========================================
    echo   服务器启动成功！
    echo   后端: http://localhost:8000
    echo   前端: http://localhost:5178
    echo ========================================
) else (
    echo.
    echo [ERROR] 服务器启动失败
)

:: 启动前端（可选）
echo.
set /p start_frontend="是否启动前端开发服务器？(y/n): "
if /i "%start_frontend%"=="y" (
    echo 启动前端...
    cd /d E:\OpenClaw\frontend
    start /B npm run dev
    echo 前端启动在 http://localhost:5178
)

echo.
echo 按任意键退出...
pause >nul
