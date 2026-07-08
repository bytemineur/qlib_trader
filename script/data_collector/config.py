# config.py
import os

HOME = os.path.expanduser('~')
QLIB_ROOT = os.path.join(HOME, '.qlib')

RAW_DATA_DIR = os.path.join(QLIB_ROOT, 'raw_data')
CSV_DIR = os.path.join(QLIB_ROOT, 'csv_data', 'cn_data')
BIN_DIR = os.path.join(QLIB_ROOT, 'qlib_data', 'cn_data')

for d in [RAW_DATA_DIR, CSV_DIR, BIN_DIR]:
    os.makedirs(d, exist_ok=True)

# Qlib dump 配置
INCLUDE_FIELDS = 'open,close,high,low,volume,factor'
DATE_FIELD = 'date'
FREQ = 'day'

# 数据获取起始日期
START_DATE = '2000-01-01'