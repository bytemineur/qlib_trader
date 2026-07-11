# ========== 极简通用版（带日志输出） ==========
$ErrorActionPreference = "Stop"

# ----- 设置日志目录和日志文件 -----
$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) { $ScriptDir = (Get-Item .).FullName }
$ProjectRoot = Split-Path $ScriptDir -Parent
$logDir = Join-Path $ProjectRoot "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir "update_qlib_data.log"

# 开始转录（所有控制台输出会同时写入日志文件）
Start-Transcript -Path $logFile -Force

# ----- 切换到 data_collector 目录 -----
$dataCollectorDir = Join-Path $ScriptDir "data_collector"
Set-Location $dataCollectorDir

# ----- 执行 step1 -----
Write-Host "Executing step1..."
conda run -n qlib python step1_get_stock_list_baostock.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# ----- 执行 step2 -----
Write-Host "Executing step2..."
conda run -n qlib python step2_fetch_and_export_baostock.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# ----- 准备数据目录 -----
$dataPath = "$env:USERPROFILE\.qlib\csv_data\cn_data"
$qlibDir  = "$env:USERPROFILE\.qlib\qlib_data\cn_data"
New-Item -ItemType Directory -Force -Path $dataPath, $qlibDir | Out-Null

# ----- 执行 step3（带参数） -----
Write-Host "Executing step3..."
conda run -n qlib python step3_dump_bin.py dump_all --data_path $dataPath --qlib_dir $qlibDir --include_fields open,close,high,low,volume,factor
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "All steps completed successfully!"

# 停止转录（日志记录结束）
Stop-Transcript