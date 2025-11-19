@echo off
REM Build AgentManager Dashboard to EXE using PyInstaller

echo ============================================================
echo   Building AgentManager Dashboard to EXE
echo ============================================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Install PyInstaller if needed
echo [INFO] Checking for PyInstaller...
python -c "import PyInstaller" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installing PyInstaller...
    python -m pip install pyinstaller
)

REM Install dependencies
echo [INFO] Installing dependencies...
python -m pip install -r app\requirements.txt

echo.
echo [INFO] Building executable...
echo [INFO] This may take 2-3 minutes...
echo.

REM Build with PyInstaller
python -m PyInstaller --name="AgentManagerDashboard" ^
    --onefile ^
    --windowed ^
    --add-data="app;app" ^
    --hidden-import=tkinter ^
    --hidden-import=tkinter.ttk ^
    --hidden-import=tkinter.scrolledtext ^
    --hidden-import=PIL ^
    --hidden-import=PIL._tkinter_finder ^
    --hidden-import=requests ^
    --clean ^
    run_dashboard.py

if %errorlevel% equ 0 (
    echo.
    echo ============================================================
    echo   BUILD SUCCESSFUL!
    echo ============================================================
    echo.
    echo Executable created: dist\AgentManagerDashboard.exe
    echo.
    echo Usage:
    echo   1. Double-click dist\AgentManagerDashboard.exe
    echo   2. Or run: .\dist\AgentManagerDashboard.exe
    echo.
    echo Note: Docker containers must be running before launching
    echo ============================================================
) else (
    echo.
    echo [ERROR] Build failed. Check error messages above.
)

pause
