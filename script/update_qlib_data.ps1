# update_qlib_data.ps1
# Purpose: Update Qlib data by running data collection and binary conversion

$ErrorActionPreference = "Stop"

# ====== 改动 1：重写 Write-Host，自动添加时间戳 ======
function Write-Host {
    param(
        [string]$Message
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    # 调用原生的 Write-Host 防止死循环，并输出带时间戳的内容
    Microsoft.PowerShell.Utility\Write-Host "[$timestamp] $Message"
}
# =====================================================

# ----- Configuration -----
$pythonExe = "C:\ProgramData\anaconda3\envs\baostock_qlib\python.exe"
if (-not (Test-Path $pythonExe)) {
    Write-Error "Python interpreter not found: $pythonExe"
    exit 1
}
# -------------------------

# ====== 新增：日志重定向 ======
$logFile = "C:\Users\zhang\Desktop\qlib_trader\logs\update_qlib_data.log"
New-Item -ItemType Directory -Force -Path (Split-Path $logFile -Parent) | Out-Null
Start-Transcript -Path $logFile -Force
# ==============================

# Change to script directory and then into data_collector subdirectory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$dataCollectorDir = Join-Path $scriptDir "data_collector"
if (-not (Test-Path $dataCollectorDir)) {
    Write-Error "data_collector directory not found: $dataCollectorDir"
    exit 1
}
Set-Location $dataCollectorDir
Write-Host "Current working directory: $(Get-Location)"
Write-Host "Using Python: $pythonExe"

function Invoke-PythonScript {
    param(
        [string]$ScriptName,
        [string[]]$Arguments = @()
    )
    Write-Host ""
    Write-Host ">>> Executing: python $ScriptName $($Arguments -join ' ')"
    
    # ====== 改动 2：管道逐行加时间戳（捕获 stdout 和 stderr） ======
    & $pythonExe $ScriptName @Arguments 2>&1 | ForEach-Object {
        Write-Host $_
    }
    # ==============================================================
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Script $ScriptName failed with exit code: $LASTEXITCODE"
        exit $LASTEXITCODE
    }
}

# Step 1: Get stock list
Invoke-PythonScript "step1_get_stock_list_baostock.py"

# Step 2: Fetch and export CSV data
Invoke-PythonScript "step2_fetch_and_export_baostock.py"

# Step 3: Dump to Qlib binary format
$homePath = $env:USERPROFILE
$dataPath = "$homePath\.qlib\csv_data\cn_data"
$qlibDir = "$homePath\.qlib\qlib_data\cn_data"

# Ensure target directories exist
New-Item -ItemType Directory -Force -Path $dataPath | Out-Null
New-Item -ItemType Directory -Force -Path $qlibDir | Out-Null

Invoke-PythonScript "step3_dump_bin.py" @("dump_all", "--data_path", $dataPath, "--qlib_dir", $qlibDir, "--include_fields", "open,close,high,low,volume,factor")

Write-Host ""
Write-Host "All steps completed successfully!"