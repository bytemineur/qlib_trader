# step2_fetch_and_export_baostock.py
import baostock as bs
import pandas as pd
import os
import time
from datetime import datetime
from config import RAW_DATA_DIR, CSV_DIR   # 确保 config.py 中 CSV_DIR 指向 ~/.qlib/csv_data/cn_data

# 配置
START_DATE = '2000-01-01'
MAX_RETRY = 3
SLEEP_SEC = 0.5   # 每只股票之间的间隔，避免请求过快

def get_symbol_and_filename(code):
    """
    从 baostock code 生成 symbol 和文件名
    例如 sh.600000 -> ('SH600000', 'SH600000.CSV')
    bj.430047 -> ('BJ430047', 'BJ430047.CSV')
    """
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
    """获取单只股票前复权日线数据，返回 DataFrame（列：date,open,high,low,close,volume）"""
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
            # 确保列名
            data.rename(columns={'volume': 'volume'}, inplace=True)
            return data[['date', 'open', 'high', 'low', 'close', 'volume']]
        except Exception as e:
            print(f"    尝试 {attempt+1}/{MAX_RETRY} 异常: {e}")
            time.sleep(2)
    return pd.DataFrame()

def save_to_csv(data, symbol, filepath):
    """将数据保存为 Qlib 格式 CSV（symbol 在第一列）"""
    if data.empty:
        return False
    export = data.copy()
    # 日期格式 YYYY-MM-DD（原始就是，但确保统一）
    export['date'] = pd.to_datetime(export['date']).dt.strftime('%Y-%m-%d')
    export['factor'] = 1
    export['symbol'] = symbol
    # 按顺序排列：symbol 放在第一列
    export = export[['symbol', 'date', 'open', 'high', 'low', 'close', 'volume', 'factor']]
    export = export.sort_values('date')
    export.to_csv(filepath, index=False)
    return True

def main():
    print("📌 全量获取前复权数据并导出 Qlib CSV (for 循环，断点续传)")
    print(f"输出目录: {CSV_DIR}")
    
    # 登录
    lg = bs.login()
    print(f"登录: {lg.error_msg}")
    if lg.error_code != '0':
        print("登录失败，退出")
        return

    # 读取股票列表
    stock_file = os.path.join(RAW_DATA_DIR, 'stock_list_baostock.csv')
    if not os.path.exists(stock_file):
        print(f"❌ 未找到 {stock_file}，请先运行 Step1")
        bs.logout()
        return
    stock_df = pd.read_csv(stock_file)
    # 如果只需要正常上市股票（status=1），取消下一行注释
    # stock_df = stock_df[stock_df['status'] == 1]
    codes = stock_df['code'].tolist()
    total = len(codes)
    print(f"总共 {total} 只股票待处理")

    # 统计已存在文件
    existing = 0
    to_process = []
    for code in codes:
        symbol, filename = get_symbol_and_filename(code)
        if symbol is None:
            continue
        filepath = os.path.join(CSV_DIR, filename)
        if os.path.exists(filepath):
            existing += 1
        else:
            to_process.append((code, symbol, filepath))
    print(f"已存在 {existing} 个 CSV 文件，将跳过")
    print(f"待处理 {len(to_process)} 只股票")

    if not to_process:
        print("所有股票已完成，无需处理")
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
        # 每只股票之间稍作停顿
        time.sleep(SLEEP_SEC)

        # 每 100 只打印一次进度
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