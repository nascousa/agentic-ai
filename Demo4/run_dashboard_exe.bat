@echo off
REM AgentManager Dashboard Executable Launcher

echo ========================================
echo   AgentManager Dashboard (EXE)
echo ========================================
echo.

REM Check if executable exists
if not exist "app\dist\AgentManagerDashboard.exe" (
    echo [ERROR] AgentManagerDashboard.exe not found in app\dist\
    echo [INFO] Please run: python -m PyInstaller --distpath app\dist --workpath app\build AgentManagerDashboard.spec --clean
    pause
    exit /b 1
)

echo [INFO] Starting AgentManager Dashboard executable...
echo [INFO] Location: app\dist\AgentManagerDashboard.exe
echo.

REM Run the dashboard executable
start "" "app\dist\AgentManagerDashboard.exe"

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Dashboard executable failed to start
    pause
    exit /b 1
)

echo [SUCCESS] Dashboard started successfully!
echo [INFO] The dashboard is now running in a separate window
echo.
pause