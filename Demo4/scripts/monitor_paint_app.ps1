#!/usr/bin/env pwsh
# Monitor paint_app workflow progress

$token = (Get-Content .env | Select-String "SERVER_API_TOKEN").ToString().Split('=')[1].Trim()
$workflow_id = "paint_app_workflow"

Write-Host "`n🎨 Paint App Workflow Monitor" -ForegroundColor Cyan
Write-Host "======================================`n" -ForegroundColor Cyan

while ($true) {
    Clear-Host
    Write-Host "`n🎨 Paint App Workflow Monitor" -ForegroundColor Cyan
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host "Workflow ID: $workflow_id" -ForegroundColor Yellow
    Write-Host "Time: $(Get-Date -Format 'HH:mm:ss')`n" -ForegroundColor Gray
    
    # Check if project folder exists
    $today = Get-Date -Format "yyyy-MM-dd"
    $projectPath = "projects\$today\paint_app"
    
    if (Test-Path $projectPath) {
        Write-Host "✅ Project folder created: $projectPath" -ForegroundColor Green
        
        if (Test-Path "$projectPath\FINAL_OUTPUT.md") {
            Write-Host "✅ FINAL_OUTPUT.md exists!" -ForegroundColor Green
            Write-Host "`n📊 Workflow complete! Opening results..." -ForegroundColor Green
            Start-Sleep -Seconds 2
            
            # Show summary
            if (Test-Path "$projectPath\workflow_summary.json") {
                $summary = Get-Content "$projectPath\workflow_summary.json" | ConvertFrom-Json
                Write-Host "`n📈 Workflow Summary:" -ForegroundColor Cyan
                Write-Host "  Total Tasks: $($summary.total_tasks)" -ForegroundColor White
                Write-Host "  Execution Time: $([math]::Round($summary.total_execution_time, 2))s" -ForegroundColor White
                Write-Host "  Agents Used: $($summary.agents_used -join ', ')" -ForegroundColor White
            }
            
            Write-Host "`n📂 Opening project folder..." -ForegroundColor Yellow
            explorer $projectPath
            break
        } else {
            Write-Host "⏳ Processing... (FINAL_OUTPUT.md not ready yet)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "⏳ Workflow in progress... (project folder not created yet)" -ForegroundColor Yellow
    }
    
    # Check worker logs for recent activity
    Write-Host "`n🔄 Recent Worker Activity:" -ForegroundColor Cyan
    $recentLogs = docker logs --since 10s agentmanager-worker-researcher-1-1 2>&1 | Select-String -Pattern "Claimed|Executing|completed" | Select-Object -Last 3
    if ($recentLogs) {
        $recentLogs | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
    } else {
        Write-Host "  (No recent activity in last 10s)" -ForegroundColor Gray
    }
    
    Write-Host "`n⏱️  Refreshing in 5 seconds... (Ctrl+C to stop)" -ForegroundColor Gray
    Start-Sleep -Seconds 5
}

Write-Host "`n✅ Monitoring complete!" -ForegroundColor Green
