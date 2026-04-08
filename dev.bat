@echo off
title Aether Dev Servers

echo Killing stale processes on ports 8080 and 5173...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8080.*LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173.*LISTENING"') do taskkill /F /PID %%a >nul 2>&1
timeout /t 1 /nobreak >nul

echo.
echo ========================================
echo   Frontend: http://localhost:5173
echo   Backend:  http://127.0.0.1:8080
echo   Close this window to stop both
echo ========================================
echo.

cd /d "%~dp0backend"
start /b python -m uvicorn aether.main:app --reload --host 127.0.0.1 --port 8080

cd /d "%~dp0frontend"
start /b npx vite --port 5173

echo Servers starting... wait a few seconds then open http://localhost:5173
echo.
pause
echo Stopping Aether servers...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8080.*LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173.*LISTENING"') do taskkill /F /PID %%a >nul 2>&1
