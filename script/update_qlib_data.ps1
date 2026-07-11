# ========== 固定使用 conda qlib 环境（带结构化日志） ==========
$ErrorActionPreference = "Stop"

# ----- 获取路径 -----
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir   # 项目根目录（qlib_trader）

# ----- 定义日志路径 -----
$logDir = Join-Path $projectRoot "logs"
$logFile = Join-Path $logDir "update_qlib_data.log"

# ----- 日志函数 -----
function Write-Log {
    param([string]$Message)
    $timeStamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timeStamp] $Message"
    Write-Host $logEntry
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Force -Path $logDir | Out-Null
    }
    Add-Content -Path $logFile -Value $logEntry -ErrorAction SilentlyContinue
}

Write-Log "========== Starting Qlib data update =========="

# ----- 切换到项目根目录（便于 Python 脚本使用相对路径） -----
Set-Location $projectRoot
Write-Log "Working directory: $(Get-Location)"

# ----- 定义 conda 命令前缀（固定使用 qlib 环境） -----
$condaCmd = "conda run -n qlib python"

# ----- Step 1: 更新 Qlib 原始数据 -----
$pyScript1 = Join-Path $scriptDir "update_qlib_data.py"
Write-Log "Step 1: Executing $condaCmd $pyScript1"

# 临时将 ErrorActionPreference 设为 Continue，避免 stderr 输出触发异常
$oldErrorAction = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$output = & conda run -n qlib python $pyScript1 2>&1
$exitCode = $LASTEXITCODE
$ErrorActionPreference = $oldErrorAction

if ($output) {
    $output | ForEach-Object { Write-Log "STEP1 OUTPUT: $_" }
}
Write-Log "Step 1 finished with exit code: $exitCode"
if ($exitCode -ne 0) {
    Write-Log "Step 1 FAILED. Aborting."
    exit $exitCode
}

# ----- 准备数据目录（与原始逻辑一致） -----
$dataPath = "$env:USERPROFILE\.qlib\csv_data\cn_data"
$qlibDir  = "$env:USERPROFILE\.qlib\qlib_data\cn_data"
New-Item -ItemType Directory -Force -Path $dataPath, $qlibDir | Out-Null
Write-Log "Data directories ensured: $dataPath, $qlibDir"

# ----- Step 2: 转换为 Qlib 二进制格式 -----
$pyScript2 = Join-Path $scriptDir "dump_bin.py"
Write-Log "Step 2: Executing $condaCmd $pyScript2 dump_all --data_path $dataPath --qlib_dir $qlibDir --include_fields open,close,high,low,volume,factor"

$oldErrorAction = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$output = & conda run -n qlib python $pyScript2 "dump_all" "--data_path" $dataPath "--qlib_dir" $qlibDir "--include_fields" "open,close,high,low,volume,factor" 2>&1
$exitCode = $LASTEXITCODE
$ErrorActionPreference = $oldErrorAction

if ($output) {
    $output | ForEach-Object { Write-Log "STEP2 OUTPUT: $_" }
}
Write-Log "Step 2 finished with exit code: $exitCode"
if ($exitCode -ne 0) {
    Write-Log "Step 2 FAILED. Aborting."
    exit $exitCode
}

Write-Log "All steps completed successfully!"
Write-Log "========== Qlib data update finished =========="