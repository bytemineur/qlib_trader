# ========== 通用版（带结构化日志） ==========
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

# ----- 确定 Python 解释器路径（优先查找 qlib conda 环境） -----
$pythonPath = $null
try {
    $condaList = & conda env list 2>$null
    if ($LASTEXITCODE -eq 0) {
        $qlibLine = $condaList | Select-String "^qlib\s"
        if ($qlibLine) {
            $envPath = ($qlibLine -split '\s+', 3)[1]
            if (Test-Path $envPath) {
                $pythonPath = Join-Path $envPath "python.exe"
                Write-Log "Using qlib conda environment at: $envPath"
            }
        }
    }
} catch {
    # conda 命令不可用，忽略
}

# 如果没找到 qlib 环境，则回退到当前激活的 conda 环境或系统 python
if (-not $pythonPath) {
    if ($env:CONDA_PREFIX) {
        $pythonPath = Join-Path $env:CONDA_PREFIX "python.exe"
        Write-Log "Using current conda environment: $env:CONDA_PREFIX"
    } else {
        $pythonPath = "python"
        Write-Log "No conda environment detected, using system python: $pythonPath"
    }
}

# ----- Step 1: 更新 Qlib 原始数据 -----
$pyScript1 = Join-Path $scriptDir "update_qlib_data.py"
Write-Log "Step 1: Executing $pyScript1"

try {
    $output = & $pythonPath $pyScript1 2>&1
    $exitCode = $LASTEXITCODE
    if ($output) {
        $output | ForEach-Object { Write-Log "STEP1 OUTPUT: $_" }
    }
    Write-Log "Step 1 finished with exit code: $exitCode"
    if ($exitCode -ne 0) {
        Write-Log "Step 1 FAILED. Aborting."
        exit $exitCode
    }
} catch {
    Write-Log "Step 1 exception: $_"
    Write-Log "Stack trace: $($_.ScriptStackTrace)"
    exit 1
}

# ----- 准备数据目录（与原始逻辑一致） -----
$dataPath = "$env:USERPROFILE\.qlib\csv_data\cn_data"
$qlibDir  = "$env:USERPROFILE\.qlib\qlib_data\cn_data"
New-Item -ItemType Directory -Force -Path $dataPath, $qlibDir | Out-Null
Write-Log "Data directories ensured: $dataPath, $qlibDir"

# ----- Step 2: 转换为 Qlib 二进制格式 -----
$pyScript2 = Join-Path $scriptDir "dump_bin.py"
Write-Log "Step 2: Executing $pyScript2 with arguments: dump_all --data_path $dataPath --qlib_dir $qlibDir --include_fields open,close,high,low,volume,factor"

try {
    $output = & $pythonPath $pyScript2 "dump_all" "--data_path" $dataPath "--qlib_dir" $qlibDir "--include_fields" "open,close,high,low,volume,factor" 2>&1
    $exitCode = $LASTEXITCODE
    if ($output) {
        $output | ForEach-Object { Write-Log "STEP2 OUTPUT: $_" }
    }
    Write-Log "Step 2 finished with exit code: $exitCode"
    if ($exitCode -ne 0) {
        Write-Log "Step 2 FAILED. Aborting."
        exit $exitCode
    }
} catch {
    Write-Log "Step 2 exception: $_"
    Write-Log "Stack trace: $($_.ScriptStackTrace)"
    exit 1
}

Write-Log "All steps completed successfully!"
Write-Log "========== Qlib data update finished =========="