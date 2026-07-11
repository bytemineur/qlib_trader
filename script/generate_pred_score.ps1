$ScriptDir = $PSScriptRoot
$ProjectRoot = Split-Path $ScriptDir -Parent
conda activate qlib
Set-Location $ProjectRoot
python script\generate_pred_score.py