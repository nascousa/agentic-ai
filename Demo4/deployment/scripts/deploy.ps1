# =============================================================================
# AgentManager - PowerShell Deployment Script
# =============================================================================

param(
    [string]$Mode = "interactive",
    [switch]$SkipServerDeploy,
    [switch]$SkipWorkerDeploy,
    [string]$WorkerMode = "individual"
)

Write-Host "🚀 AgentManager PowerShell Deployment Script" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# Check Docker installation
try {
    $dockerVersion = docker --version
    Write-Host "[SUCCESS] Docker is installed: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Docker is not installed. Please install Docker Desktop first." -ForegroundColor Red
    exit 1
}

try {
    $composeVersion = docker-compose --version
    Write-Host "[SUCCESS] Docker Compose is installed: $composeVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Docker Compose is not installed. Please install Docker Compose first." -ForegroundColor Red
    exit 1
}

# Generate secure tokens
Write-Host "[INFO] Generating secure tokens..." -ForegroundColor Yellow
$AUTH_TOKEN = [System.Web.Security.Membership]::GeneratePassword(43, 0)
$SECRET_KEY = [System.Web.Security.Membership]::GeneratePassword(86, 0)
Write-Host "[SUCCESS] Secure tokens generated" -ForegroundColor Green

# Setup environment file
Write-Host "[INFO] Setting up environment configuration..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Copy-Item ".env.template" ".env"
    Write-Host "[SUCCESS] Created .env file from template" -ForegroundColor Green
    
    # Replace tokens in .env file
    $envContent = Get-Content ".env" -Raw
    $envContent = $envContent -replace 'your_secure_server_api_token_here', $AUTH_TOKEN
    $envContent = $envContent -replace 'your_secure_secret_key_here', $SECRET_KEY
    Set-Content ".env" $envContent
    
    Write-Host "[WARNING] Please edit .env file and add your OPENAI_API_KEY and other configuration" -ForegroundColor Yellow
    if ($Mode -eq "interactive") {
        Read-Host "Press Enter to continue after editing .env file"
    }
} else {
    Write-Host "[WARNING] .env file already exists. Skipping creation." -ForegroundColor Yellow
}

# Create necessary directories
@("logs", "temp", "config") | ForEach-Object {
    if (-not (Test-Path $_)) {
        New-Item -ItemType Directory -Path $_ | Out-Null
        Write-Host "[INFO] Created directory: $_" -ForegroundColor Cyan
    }
}

# Deploy server
if (-not $SkipServerDeploy) {
    Write-Host "[INFO] Deploying AgentManager Server..." -ForegroundColor Yellow
    Set-Location "server"
    docker-compose up -d --build
    Set-Location ".."
    Write-Host "[SUCCESS] Server deployment started" -ForegroundColor Green
    
    # Wait for server to be ready
    Write-Host "[INFO] Waiting for server to be ready..." -ForegroundColor Yellow
    Start-Sleep 10
}

# Deploy workers
if (-not $SkipWorkerDeploy) {
    Write-Host "[INFO] Deploying AgentManager Workers..." -ForegroundColor Yellow
    Set-Location "worker"
    
    if ($Mode -eq "interactive") {
        Write-Host "Select worker deployment mode:" -ForegroundColor Cyan
        Write-Host "1) Individual workers (researcher, analyst, writer)" -ForegroundColor White
        Write-Host "2) Multi-role worker (all capabilities in one container)" -ForegroundColor White
        Write-Host "3) Both individual and multi-role workers" -ForegroundColor White
        $choice = Read-Host "Enter your choice (1-3)"
    } else {
        $choice = switch ($WorkerMode) {
            "individual" { "1" }
            "multi-role" { "2" }
            "both" { "3" }
            default { "1" }
        }
    }
    
    switch ($choice) {
        "1" {
            docker-compose up -d --build worker-researcher worker-analyst worker-writer
        }
        "2" {
            docker-compose --profile multi-worker up -d --build worker-multi
        }
        "3" {
            docker-compose --profile multi-worker up -d --build
        }
        default {
            Write-Host "[ERROR] Invalid choice. Deploying individual workers by default." -ForegroundColor Red
            docker-compose up -d --build worker-researcher worker-analyst worker-writer
        }
    }
    
    Set-Location ".."
    Write-Host "[SUCCESS] Worker deployment started" -ForegroundColor Green
}

# Show deployment status
Write-Host "[INFO] Deployment Status:" -ForegroundColor Yellow
Write-Host ""

if (-not $SkipServerDeploy) {
    Write-Host "[INFO] Server containers:" -ForegroundColor Cyan
    Set-Location "server"
    docker-compose ps
    Set-Location ".."
    Write-Host ""
}

if (-not $SkipWorkerDeploy) {
    Write-Host "[INFO] Worker containers:" -ForegroundColor Cyan
    Set-Location "worker"
    docker-compose ps
    Set-Location ".."
    Write-Host ""
}

Write-Host "[INFO] Available endpoints:" -ForegroundColor Cyan
Write-Host "  🌐 Server API: http://localhost:8000" -ForegroundColor White
Write-Host "  📚 API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host "  ❤️ Health Check: http://localhost:8000/health" -ForegroundColor White
Write-Host ""
Write-Host "[INFO] Worker metrics:" -ForegroundColor Cyan
Write-Host "  📊 Researcher: http://localhost:8081" -ForegroundColor White
Write-Host "  📊 Analyst: http://localhost:8082" -ForegroundColor White
Write-Host "  📊 Writer: http://localhost:8083" -ForegroundColor White
Write-Host "  📊 Multi-role: http://localhost:8084" -ForegroundColor White
Write-Host ""

Write-Host "[SUCCESS] 🎉 AgentManager deployment completed!" -ForegroundColor Green
Write-Host "[INFO] You can now submit tasks to: http://localhost:8000/v1/tasks" -ForegroundColor Cyan

if ($Mode -eq "interactive") {
    Read-Host "Press Enter to exit"
}