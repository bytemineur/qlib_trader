# 获取脚本所在目录（script文件夹）和项目根目录
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir   # 项目根目录

# 定义基于项目根目录的路径（日志和临时下载目录）
$logDir = Join-Path $projectRoot "logs"
$logFile = Join-Path $logDir "update_qlib_data.log"
$tempDir = Join-Path $projectRoot "temp"
$output = Join-Path $tempDir "qlib_bin.tar.gz"

# 目标数据目录保持绝对路径（用户目录下）
$targetDir = "$HOME\.qlib\qlib_data\cn_data"

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

Write-Log "========== Starting data update =========="

# 切换到项目根目录
Set-Location $projectRoot

$url = "https://github.com/chenditc/investment_data/releases/latest/download/qlib_bin.tar.gz"

# 确保必要目录存在
New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null

# 下载
Write-Log "Downloading from $url ..."
try {
    Invoke-WebRequest -Uri $url -OutFile $output -ErrorAction Stop
    Write-Log "Download completed, file size: $((Get-Item $output).Length) bytes"
}
catch {
    Write-Log "Download failed: $_"
    exit 1
}

# 解压
Write-Log "Extracting to $targetDir ..."
try {
    tar -xzvf $output -C $targetDir --strip-components=1
    if ($LASTEXITCODE -ne 0) {
        throw "tar extraction failed with exit code $LASTEXITCODE"
    }
    Write-Log "Extraction successful"
}
catch {
    Write-Log "Extraction failed: $_"
    exit 1
}

# 清理临时压缩包
Remove-Item -Force $output -ErrorAction SilentlyContinue
Write-Log "Cleanup done"
Write-Log "========== Data update finished =========="