# step2_fetch_and_export_baostock.py
import baostock as bs
import pandas as pd
import os
import time
from datetime import datetime
from config import RAW_DATA_DIR, CSV_DIR

# 配置
START_DATE = '2000-01-01'
MAX_RETRY = 3
SLEEP_SEC = 0.5

def get_symbol_and_filename(code):
    parts = code.split('.')
    if len(parts) != 2:
        return None, None
    prefix, num = parts
    prefix_upper = prefix.upper()
    if prefix_upper not in ['SH', 'SZ', 'BJ']:
        print(f"  未知前缀: {prefix}, 跳过")
        return None, None
    symbol = f"{prefix_upper}{num}"
    filename = f"{symbol}.CSV"
    return symbol, filename

def fetch_stock_data(code):
    today = datetime.now().strftime('%Y-%m-%d')
    fields = "date,open,high,low,close,volume"
    for attempt in range(MAX_RETRY):
        try:
            rs = bs.query_history_k_data_plus(
                code,
                fields,
                start_date=START_DATE,
                end_date=today,
                adjustflag='2',
                frequency="d"
            )
            if rs.error_code != '0':
                print(f"    尝试 {attempt+1}/{MAX_RETRY} 错误: {rs.error_msg}")
                time.sleep(2)
                continue
            data = rs.get_data()
            if data.empty:
                return pd.DataFrame()
            data.rename(columns={'volume': 'volume'}, inplace=True)
            return data[['date', 'open', 'high', 'low', 'close', 'volume']]
        except Exception as e:
            print(f"    尝试 {attempt+1}/{MAX_RETRY} 异常: {e}")
            time.sleep(2)
    return pd.DataFrame()

def save_to_csv(data, symbol, filepath):
    if data.empty:
        return False
    export = data.copy()
    export['date'] = pd.to_datetime(export['date']).dt.strftime('%Y-%m-%d')
    export['factor'] = 1
    export['symbol'] = symbol
    export = export[['symbol', 'date', 'open', 'high', 'low', 'close', 'volume', 'factor']]
    export = export.sort_values('date')
    export.to_csv(filepath, index=False)
    return True

def main():
    print("📌 全量获取前复权数据并导出 Qlib CSV (覆盖已存在的文件)")
    print(f"输出目录: {CSV_DIR}")
    
    lg = bs.login()
    print(f"登录: {lg.error_msg}")
    if lg.error_code != '0':
        print("登录失败，退出")
        return

    stock_file = os.path.join(RAW_DATA_DIR, 'stock_list_baostock.csv')
    if not os.path.exists(stock_file):
        print(f"❌ 未找到 {stock_file}，请先运行 Step1")
        bs.logout()
        return
    stock_df = pd.read_csv(stock_file)
    # 如果需要只获取正常上市股票，取消下一行注释
    # stock_df = stock_df[stock_df['status'] == 1]
    codes = stock_df['code'].tolist()
    total = len(codes)
    print(f"总共 {total} 只股票")

    # ---------- 修改点：不再跳过已存在文件，全部处理 ----------
    to_process = []
    for code in codes:
        symbol, filename = get_symbol_and_filename(code)
        if symbol is not None:
            filepath = os.path.join(CSV_DIR, filename)
            to_process.append((code, symbol, filepath))
    print(f"将处理 {len(to_process)} 只股票（覆盖已有文件）")
    # -------------------------------------------------------

    if not to_process:
        print("没有股票可处理")
        bs.logout()
        return

    success = 0
    fail = 0
    start_time = time.time()

    for idx, (code, symbol, filepath) in enumerate(to_process, 1):
        print(f"[{idx}/{len(to_process)}] 正在处理 {code} -> {symbol}.CSV ...", end='')
        data = fetch_stock_data(code)
        if data.empty:
            print(" 无数据")
            fail += 1
        else:
            ok = save_to_csv(data, symbol, filepath)
            if ok:
                print(" 完成")
                success += 1
            else:
                print(" 保存失败")
                fail += 1
        time.sleep(SLEEP_SEC)

        if idx % 100 == 0:
            elapsed = time.time() - start_time
            print(f"  进度: {idx}/{len(to_process)}, 成功: {success}, 失败: {fail}, 用时: {elapsed:.1f}s")

    elapsed = time.time() - start_time
    print("\n" + "="*60)
    print(f"✅ 处理完成！")
    print(f"  成功生成: {success} 个 CSV")
    print(f"  失败（无数据）: {fail} 个")
    print(f"  总用时: {elapsed:.1f} 秒")
    print(f"CSV 目录: {CSV_DIR}")
    print("="*60)

    bs.logout()

if __name__ == '__main__':
    main()