# ========== CreateScheduledTasks.ps1 (No admin check) ==========
$ScriptDir = $PSScriptRoot
$ProjectRoot = Split-Path $ScriptDir -Parent

schtasks /delete /tn "QlibDataUpdate" /f 2>$null
schtasks /delete /tn "QlibPredictionScore" /f 2>$null

schtasks /create /tn "QlibDataUpdate" /tr "powershell -ExecutionPolicy Bypass -File `"$ProjectRoot\script\update_qlib_data.ps1`"" /sc daily /st 20:00 /f
schtasks /create /tn "QlibPredictionScore" /tr "powershell -ExecutionPolicy Bypass -File `"$ProjectRoot\script\generate_pred_score.ps1`"" /sc daily /st 23:00 /f

Write-Host "Done."