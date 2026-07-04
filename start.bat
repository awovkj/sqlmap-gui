@echo off
chcp 65001 >nul 2>&1
title SQLmap GUI 2.0

echo ========================================
echo   SQLmap GUI 2.0 - Starting...
echo ========================================
echo.

:: Check Node.js
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found. Please install Node.js first.
    echo Download: https://nodejs.org/
    pause
    exit /b 1
)

:: Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python first.
    echo Download: https://python.org/
    pause
    exit /b 1
)

:: Install dependencies (first run)
if not exist "node_modules" (
    echo [1/3] Installing frontend dependencies...
    call npm install
    echo.
)

:: Install Python dependencies
echo [2/3] Checking Python dependencies...
python -m pip install -r requirements.txt -q 2>nul

echo [3/3] Starting application...
echo.
echo ----------------------------------------
echo   Application will start automatically
echo   Press Ctrl+C to stop
echo ----------------------------------------
echo.

call npm start
pause
