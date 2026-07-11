# ========== CreateScheduledTasks.ps1 (English version) ==========
# Purpose: Create/update daily scheduled tasks for Qlib data update and prediction
# Requirement: Run as Administrator

# ---------- Check admin rights ----------
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "Please run this script as Administrator!" -ForegroundColor Red
    exit 1
}

# ---------- Locate project root dynamically ----------
$ScriptDir = $PSScriptRoot
$ParentDir = Split-Path $ScriptDir -Parent

if (Test-Path (Join-Path $ParentDir "script")) {
    $ProjectRoot = $ParentDir
} else {
    $ProjectRoot = $ScriptDir
}

Write-Host "Project root detected: $ProjectRoot" -ForegroundColor Cyan

# ---------- Build paths to business scripts ----------
$UpdateScript   = Join-Path $ProjectRoot "script\update_qlib_data.ps1"
$PredictScript  = Join-Path $ProjectRoot "script\generate_pred_score.ps1"

if (-not (Test-Path $UpdateScript)) {
    Write-Error "Update script not found: $UpdateScript"
    exit 1
}
if (-not (Test-Path $PredictScript)) {
    Write-Error "Prediction script not found: $PredictScript"
    exit 1
}

# ---------- Define tasks ----------
$tasks = @(
    @{
        Name    = "QlibDataUpdate"
        Command = "powershell -ExecutionPolicy Bypass -File `"$UpdateScript`""
        Time    = "20:00"
    },
    @{
        Name    = "QlibPredictionScore"
        Command = "powershell -ExecutionPolicy Bypass -File `"$PredictScript`""
        Time    = "23:00"
    }
)

# ---------- Create/update tasks ----------
foreach ($task in $tasks) {
    $existing = schtasks /query /tn $task.Name 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Task '$($task.Name)' already exists, deleting and recreating..." -ForegroundColor Yellow
        schtasks /delete /tn $task.Name /f | Out-Null
    }
    
    schtasks /create /tn $task.Name /tr $task.Command /sc daily /st $task.Time /f
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Task '$($task.Name)' created successfully!" -ForegroundColor Green
    } else {
        Write-Host "Task '$($task.Name)' creation failed. Please check error messages." -ForegroundColor Red
    }
}