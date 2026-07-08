# update_qlib_data.ps1
# 全量更新 Qlib 数据：从 BaoStock 获取并转换为 bin 格式
# 支持断点续传（如果某一步已完成，自动跳过）

# ---------- 配置 ----------
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$logDir = Join-Path $projectRoot "logs"
$logFile = Join-Path $logDir "update_qlib_data.log"
$csvDir = "$HOME\.qlib\csv_data\cn_data"
$binDir = "$HOME\.qlib\qlib_data\cn_data"
$stockListFile = "$HOME\.qlib\raw_data\stock_list_baostock.csv"

# 创建日志目录
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
}

# ---------- 日志函数 ----------
function Write-Log {
    param([string]$Message)
    $timeStamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timeStamp] $Message"
    Write-Host $logEntry
    Add-Content -Path $logFile -Value $logEntry -ErrorAction SilentlyContinue
}

# ---------- 错误处理 ----------
function Check-Error {
    if ($LASTEXITCODE -ne 0) {
        Write-Log "❌ 上一步执行失败，退出脚本。"
        exit $LASTEXITCODE
    }
}

# ---------- 检查步骤是否已完成 ----------
function Step-Done {
    param([string]$StepName, [scriptblock]$CheckCondition)
    if (& $CheckCondition) {
        Write-Log "✅ $StepName 已完成，跳过。"
        return $true
    }
    return $false
}

# ---------- 主流程 ----------
Write-Log "========================================"
Write-Log "开始全量数据更新流程"
Write-Log "项目目录: $projectRoot"

# 1. 激活 Conda 环境（使用 conda run）
Write-Log "Step 1: 激活 conda 环境 baostock_qlib"
conda run -n baostock_qlib python -c "import sys; print(sys.executable)" | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Log "❌ 无法激活环境，请确认 conda 已安装且环境 baostock_qlib 存在"
    exit 1
}
Write-Log "✅ 环境激活成功"

# 2. 获取股票列表（如果文件已存在则跳过）
$step2Done = Step-Done "获取股票列表" { Test-Path $stockListFile }
if (-not $step2Done) {
    Write-Log "Step 2: 执行 step1_get_stock_list_baostock.py"
    conda run -n baostock_qlib python $projectRoot\step1_get_stock_list_baostock.py
    Check-Error
    Write-Log "✅ 股票列表获取完成"
} else {
    Write-Log "Step 2: 跳过（股票列表已存在）"
}

# 3. 获取全量日线数据并导出 CSV（如果 CSV 目录已有文件则跳过，但这里不强制，由 step2 内部实现断点续传）
Write-Log "Step 3: 执行 step2_fetch_and_export_baostock.py"
# 该脚本内部会跳过已存在的 CSV，所以即使重跑也无害
conda run -n baostock_qlib python $projectRoot\step2_fetch_and_export_baostock.py
Check-Error
Write-Log "✅ CSV 导出完成"

# 4. 转换为 Qlib bin 格式（如果 bin 目录已有 calendars 目录则跳过）
$step4Done = Step-Done "转换为 Qlib bin" { Test-Path "$binDir\calendars" }
if (-not $step4Done) {
    Write-Log "Step 4: 执行 step3_dump_bin.py dump_all"
    $fields = "open,close,high,low,volume,factor"
    conda run -n baostock_qlib python $projectRoot\step3_dump_bin.py dump_all `
        --csv_path $csvDir `
        --qlib_dir $binDir `
        --include_fields $fields
    Check-Error
    Write-Log "✅ Qlib bin 数据生成完成"
} else {
    Write-Log "Step 4: 跳过（bin 数据已存在）"
}

Write-Log "========================================"
Write-Log "🎉 所有步骤执行成功！"
Write-Log "输出目录: $binDir"