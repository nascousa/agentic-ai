@echo off
REM Start AgentManager Worker Client
echo Starting AgentManager Worker Client...
echo.
D:\Repos\AgentManager\.venv\Scripts\python.exe client_worker.py --config mcp_client_config.json
pause
