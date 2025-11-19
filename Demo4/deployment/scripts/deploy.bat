@echo off
REM =============================================================================
REM AgentManager - Windows Deployment Script
REM =============================================================================

setlocal enabledelayedexpansion

echo 🚀 AgentManager Windows Deployment Script
echo ==========================================

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not installed. Please install Docker Desktop first.
    pause
    exit /b 1
)

docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Compose is not installed. Please install Docker Compose first.
    pause
    exit /b 1
)

echo [SUCCESS] Docker and Docker Compose are installed

REM Generate secure tokens
echo [INFO] Generating secure tokens...
for /f "delims=" %%i in ('python -c "import secrets; print(secrets.token_urlsafe(32))"') do set AUTH_TOKEN=%%i
for /f "delims=" %%i in ('python -c "import secrets; print(secrets.token_urlsafe(64))"') do set SECRET_KEY=%%i
echo [SUCCESS] Secure tokens generated

REM Setup environment file
echo [INFO] Setting up environment configuration...
if not exist .env (
    copy .env.template .env
    echo [SUCCESS] Created .env file from template
    
    REM Replace tokens in .env file
    powershell -Command "(gc .env) -replace 'your_secure_server_api_token_here', '%AUTH_TOKEN%' | Out-File -encoding ASCII .env"
    powershell -Command "(gc .env) -replace 'your_secure_secret_key_here', '%SECRET_KEY%' | Out-File -encoding ASCII .env"
    
    echo [WARNING] Please edit .env file and add your OPENAI_API_KEY and other configuration
    pause
) else (
    echo [WARNING] .env file already exists. Skipping creation.
)

REM Create necessary directories
if not exist logs mkdir logs
if not exist temp mkdir temp
if not exist config mkdir config

REM Deploy server
echo [INFO] Deploying AgentManager Server...
cd server
docker-compose up -d --build
cd ..
echo [SUCCESS] Server deployment started

REM Wait for server to be ready
echo [INFO] Waiting for server to be ready...
timeout /t 10 /nobreak >nul

REM Deploy workers
echo [INFO] Deploying AgentManager Workers...
cd worker

echo Select worker deployment mode:
echo 1) Individual workers (researcher, analyst, writer)
echo 2) Multi-role worker (all capabilities in one container)
echo 3) Both individual and multi-role workers
set /p choice="Enter your choice (1-3): "

if "%choice%"=="1" (
    docker-compose up -d --build worker-researcher worker-analyst worker-writer
) else if "%choice%"=="2" (
    docker-compose --profile multi-worker up -d --build worker-multi
) else if "%choice%"=="3" (
    docker-compose --profile multi-worker up -d --build
) else (
    echo [ERROR] Invalid choice. Deploying individual workers by default.
    docker-compose up -d --build worker-researcher worker-analyst worker-writer
)

cd ..
echo [SUCCESS] Worker deployment started

REM Show deployment status
echo [INFO] Deployment Status:
echo.
echo [INFO] Server containers:
cd server
docker-compose ps
cd ..

echo.
echo [INFO] Worker containers:
cd worker
docker-compose ps
cd ..

echo.
echo [INFO] Available endpoints:
echo   🌐 Server API: http://localhost:8000
echo   📚 API Docs: http://localhost:8000/docs
echo   ❤️ Health Check: http://localhost:8000/health
echo.
echo [INFO] Worker metrics:
echo   📊 Researcher: http://localhost:8081
echo   📊 Analyst: http://localhost:8082
echo   📊 Writer: http://localhost:8083
echo   📊 Multi-role: http://localhost:8084

echo.
echo [SUCCESS] 🎉 AgentManager deployment completed!
echo [INFO] You can now submit tasks to: http://localhost:8000/v1/tasks

pause