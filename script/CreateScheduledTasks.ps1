# 需要管理员权限
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "请以管理员身份运行此脚本！" -ForegroundColor Red
    exit 1
}

$tasks = @(
    @{
        Name    = "Qlib数据更新"
        Command = "powershell -ExecutionPolicy Bypass -File C:\Users\zhh\Desktop\qlib_trader\script\update_qlib_data.ps1"
        Time    = "20:00"
    },
    @{
        Name    = "Qlib预测分数"
        Command = "powershell -ExecutionPolicy Bypass -File C:\Users\zhh\Desktop\qlib_trader\script\generate_pred_score.ps1"
        Time    = "23:00"
    }
)

foreach ($task in $tasks) {
    $existing = schtasks /query /tn $task.Name 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "任务 '$($task.Name)' 已存在，将先删除再重建..." -ForegroundColor Yellow
        schtasks /delete /tn $task.Name /f | Out-Null
    }
    
    schtasks /create /tn $task.Name /tr $task.Command /sc daily /st $task.Time /f
    if ($LASTEXITCODE -eq 0) {
        Write-Host "任务 '$($task.Name)' 创建成功！" -ForegroundColor Green
    }
    else {
        Write-Host "任务 '$($task.Name)' 创建失败，请检查错误信息。" -ForegroundColor Red
    }
}