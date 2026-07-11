# ========== 极简通用版（无需任何路径） ==========
$ErrorActionPreference = "Stop"

$ScriptDir = $PSScriptRoot
if (-not $ScriptDir) { $ScriptDir = (Get-Item .).FullName }
$dataCollectorDir = Join-Path $ScriptDir "data_collector"
Set-Location $dataCollectorDir

Write-Host "Executing step1..."
conda run -n qlib python step1_get_stock_list_baostock.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Executing step2..."
conda run -n qlib python step2_fetch_and_export_baostock.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$dataPath = "$env:USERPROFILE\.qlib\csv_data\cn_data"
$qlibDir  = "$env:USERPROFILE\.qlib\qlib_data\cn_data"
New-Item -ItemType Directory -Force -Path $dataPath, $qlibDir | Out-Null

Write-Host "Executing step3..."
conda run -n qlib python step3_dump_bin.py dump_all --data_path $dataPath --qlib_dir $qlibDir --include_fields open,close,high,low,volume,factor
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "All steps completed successfully!"