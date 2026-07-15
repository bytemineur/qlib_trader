import os
import pandas as pd
from datetime import datetime
from tqdm import tqdm
from xtquant import xtdata


# 定义回调函数，打印实时进度
def on_progress(data):
    # data 是一个字典，例如：{'finished': 150, 'total': 500}
    print(f"下载进度: {data['finished']}/{data['total']}")

# 1. 获取全部A股股票代码（沪深）
# '沪深A股' 包含了上海、深圳证券交易所的全部A股
stock_list = xtdata.get_stock_list_in_sector("沪深A股")
print(f"获取到 {len(stock_list)} 只股票")

# 2. 下载所有股票的历史日线数据到本地缓存
# 这是必须的步骤，数据需要先下载才能获取
print("开始下载历史数据...")
xtdata.download_history_data2(
    stock_list=stock_list,   # 股票列表
    period='1d',             # 日线数据
    start_time='20000101',   # 起始日期，格式 YYYYMMDD
    end_time=datetime.now().strftime('%Y%m%d'),     # 结束日期
    callback=on_progress,
    incrementally=True       # 增量下载，只下载缺失部分
)

# 3. 批量获取前复权数据
print("开始获取前复权数据...")
data_dict = xtdata.get_market_data_ex(
    field_list=['open', 'high', 'low', 'close', 'volume'],  # 需要的字段
    stock_list=stock_list,           # 股票列表
    period='1d',                     # 日线周期
    start_time='20000101',
    end_time=datetime.now().strftime('%Y%m%d'),
    dividend_type='front',           # 关键参数：前复权
    fill_data=True                   # 填充缺失数据
)

# 4. 保存为CSV文件（带进度条）
save_dir = os.path.expanduser("~/.qlib/csv_data/cn_data")
os.makedirs(save_dir, exist_ok=True)
print(f"开始保存CSV文件至：{save_dir}")

# 使用 tqdm 包装 data_dict.items()
for code, df in tqdm(data_dict.items(), desc="保存CSV文件", unit="只"):
    suffix = code.split('.')[-1].upper()
    num_part = code.split('.')[0]
    symbol_str = f"{suffix}{num_part}"
    
    # 重置索引
    df_reset = df.reset_index()
    df_reset.rename(columns={'index': 'date'}, inplace=True)
    
    # 格式化日期
    if not pd.api.types.is_datetime64_any_dtype(df_reset['date']):
        df_reset['date'] = pd.to_datetime(df_reset['date'])
    df_reset['date'] = df_reset['date'].dt.strftime('%Y-%m-%d')
    
    # 添加 symbol 和 factor
    df_reset['symbol'] = symbol_str
    df_reset['factor'] = 1
    
    # 调整列顺序
    ordered_cols = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume', 'factor']
    df_final = df_reset[ordered_cols]
    
    # 保存（无索引）
    filepath = os.path.join(save_dir, f"{symbol_str}.csv")
    df_final.to_csv(filepath, index=False)
    
    # 可选：在进度条下方显示当前保存的文件名（更直观）
    tqdm.write(f"已保存: {symbol_str}.csv")

print("所有CSV文件保存完成！")
