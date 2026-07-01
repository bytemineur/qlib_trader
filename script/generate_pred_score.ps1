# 获取脚本所在目录（script文件夹）和项目根目录
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir   # 项目根目录

# 定义日志路径（项目根目录/logs/）
$logDir = Join-Path $projectRoot "logs"
$logFile = Join-Path $logDir "generate_pred_score.log"

# 日志函数
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

Write-Log "========== Starting prediction score generation =========="

# 切换到项目根目录（方便 Python 脚本中引用相对路径，如 ml/pred_score.csv）
Set-Location $projectRoot
Write-Log "Working directory: $(Get-Location)"

# 确定 Python 解释器路径：优先查找名为 "qlib" 的 conda 环境
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

# Python 脚本位于 script/ 下
$pyScript = Join-Path $scriptDir "generate_pred_score.py"
Write-Log "Executing: $pythonPath $pyScript"

try {
    $output = & $pythonPath $pyScript 2>&1
    $exitCode = $LASTEXITCODE
    
    if ($output) {
        $output | ForEach-Object { Write-Log "OUTPUT: $_" }
    }
    
    Write-Log "Process finished with exit code: $exitCode"
    
    if ($exitCode -eq 0) {
        Write-Log "Prediction score generation SUCCESSFUL."
    }
    else {
        Write-Log "Prediction score generation FAILED with exit code $exitCode."
        exit $exitCode
    }
}
catch {
    Write-Log "Exception occurred: $_"
    Write-Log "Stack trace: $($_.ScriptStackTrace)"
    exit 1
}

Write-Log "========== Prediction score generation finished =========="