$ScriptDir = $PSScriptRoot
$ProjectRoot = Split-Path $ScriptDir -Parent
conda activate qlib
Set-Location $ProjectRoot
python script\update_qlib_data.py
python script\dump_bin.py dump_all --data_path "$env:USERPROFILE\.qlib\csv_data\cn_data" --qlib_dir "$env:USERPROFILE\.qlib\qlib_data\cn_data" --include_fields open,close,high,low,volume,factor