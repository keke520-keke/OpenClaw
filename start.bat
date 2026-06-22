@echo off
cd /d "%~dp0"

echo ========================================
echo   OpenClaw - AI Quant Trading System
echo ========================================
echo.

:: === Check Python ===
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found
    echo Install from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH"
    pause & exit /b 1
)
echo [OK] Python found

:: === Check Node ===
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found
    echo Install from: https://nodejs.org/
    pause & exit /b 1
)
echo [OK] Node.js found

:: === Backend ===
cd backend
echo.
echo === Installing backend dependencies ===
pip install -r requirements.txt -q 2>nul
echo [OK] Dependencies ready

echo === Starting backend (port 8000) ===
start "OpenClaw-Backend" cmd /c "cd /d %cd% && python -m uvicorn main:app --host 0.0.0.0 --port 8000"

echo Waiting for backend to be ready...
:wait_be
timeout /t 2 /nobreak >nul
curl -s http://localhost:8000/api/health >nul 2>&1
if %errorlevel% neq 0 goto wait_be
echo [OK] Backend running at http://localhost:8000

:: === Frontend ===
cd /d "%~dp0frontend"
echo.
echo === Installing frontend dependencies ===
call npm install 2>&1
echo [OK] Dependencies ready

echo === Starting frontend (port 5178) ===
start "OpenClaw-Frontend" cmd /c "cd /d %cd% && npm run dev -- --host 0.0.0.0 --port 5178"

echo Waiting for frontend to be ready...
:wait_fe
timeout /t 2 /nobreak >nul
curl -s http://localhost:5178 >nul 2>&1
if %errorlevel% neq 0 goto wait_fe
echo [OK] Frontend running at http://localhost:5178

:: === Open browser ===
echo.
echo ========================================
echo   Opening browser...
echo ========================================
start http://localhost:5178
echo.
echo Both servers running. Close the two cmd windows to stop.
pause
