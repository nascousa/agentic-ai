@echo off
REM AgentManager Dashboard Launcher for Windows

echo ========================================
echo   AgentManager Dashboard Launcher
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8+ from python.org
    pause
    exit /b 1
)

REM Check if required packages are installed
echo [INFO] Checking dependencies...
python -c "import tkinter" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] tkinter is not available
    echo Please install tkinter for your Python version
    pause
    exit /b 1
)

python -c "import requests" >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] requests package not found
    echo [INFO] Installing requirements...
    python -m pip install -r app\requirements.txt
)

echo [INFO] Starting AgentManager Dashboard...
echo.

REM Run the dashboard
python run_dashboard.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Dashboard failed to start
    pause
)
