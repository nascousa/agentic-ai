# Activate the Python virtual environment for AgentManager
Write-Host "Activating AgentManager virtual environment..." -ForegroundColor Green
& .\.venv\Scripts\Activate.ps1
Write-Host "✅ Virtual environment activated!" -ForegroundColor Green
Write-Host ""
Write-Host "Available commands:" -ForegroundColor Yellow
Write-Host "  python          - Run Python in venv" -ForegroundColor White
Write-Host "  pip             - Install packages in venv" -ForegroundColor White  
Write-Host "  pytest          - Run tests" -ForegroundColor White
Write-Host "  uvicorn         - Start FastAPI server" -ForegroundColor White
Write-Host "  black           - Format code" -ForegroundColor White
Write-Host "  mypy            - Type checking" -ForegroundColor White
Write-Host ""