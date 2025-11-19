@echo off
REM Activate the Python virtual environment for AgentManager
echo Activating AgentManager virtual environment...
call .venv\Scripts\activate.bat
echo ✅ Virtual environment activated!
echo.
echo Available commands:
echo   python          - Run Python in venv
echo   pip             - Install packages in venv  
echo   pytest          - Run tests
echo   uvicorn         - Start FastAPI server
echo   black           - Format code
echo   mypy            - Type checking
echo.