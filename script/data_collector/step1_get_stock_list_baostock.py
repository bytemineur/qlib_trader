# step1_get_stock_list_baostock.py
import baostock as bs
import pandas as pd
import os
from config import RAW_DATA_DIR

def main():
    print("📌 Step 1 (BaoStock): 获取A股股票列表")
    lg = bs.login()
    print(f"登录: {lg.error_msg}")

    rs = bs.query_stock_basic()
    if rs.error_code != '0':
        print(f"失败: {rs.error_msg}")
        bs.logout()
        return

    stock_df = rs.get_data()
    # 只保留股票（type=1），剔除指数、基金等
    stock_df = stock_df[stock_df['type'] == '1']
    print(f"股票数量: {len(stock_df)}")

    filepath = os.path.join(RAW_DATA_DIR, 'stock_list_baostock.csv')
    stock_df.to_csv(filepath, index=False)
    print(f"✅ 已保存至 {filepath}")
    print(stock_df.head())

    bs.logout()

if __name__ == '__main__':
    main()