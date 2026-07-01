# generate_pred_score.py
import pickle
import yaml
import multiprocessing as mp
from pathlib import Path

import qlib
from qlib.data import D
from qlib.contrib.data.handler import Alpha158
from qlib.data.dataset import DatasetH

# 加载配置文件
def load_config():
    project_root = Path(__file__).parent.parent
    config_path = project_root / "configs" / "config.yaml"
    
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件未找到: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

CONFIG = load_config()

def main():
    # 1. 加载训练好的模型
    model_path = CONFIG['model_path']
    with open(model_path, "rb") as f:
        model = pickle.load(f)
    print("模型加载成功！", type(model))

    # 2. 获取最新交易日
    qlib.init()   # 初始化 Qlib（在 main 中调用，避免子进程重复执行）
    calendar = D.calendar(freq="day")
    latest_day = calendar[-1]
    print(f"最新交易日: {latest_day}")

    # 3. 准备数据处理器
    start_time = calendar[-90]   # 取前90天作为数据起始
    end_time = latest_day

    handler = Alpha158(
        instruments="csiall",
        start_time=start_time,
        end_time=end_time,
        infer_processors=[],      # 推理时不要拟合任何处理器
    )
    print("数据处理器初始化完成。")

    # 4. 构造 Dataset 对象
    dataset = DatasetH(handler, segments={"all": (start_time, end_time)})
    print("Dataset 对象构建完成。")

    # 5. 使用模型进行预测
    pred_score = model.predict(dataset, segment="all")
    print("预测分数形状：", pred_score.shape)
    print("前5行预览：\n", pred_score.tail())

    # 6. 保存 pred_score.csv
    csv_path = Path(__file__).parent.parent / 'ml' / 'pred_score.csv'
    csv_path.parent.mkdir(parents=True, exist_ok=True)   # 确保 ml/ 目录存在
    latest_pred = pred_score.xs(latest_day, level=0)
    latest_pred.name = 'score'
    latest_pred.to_csv(csv_path, index=True, encoding="utf-8-sig")
    print(f"预测分数文件已保存至：{csv_path}")

if __name__ == '__main__':
    mp.freeze_support()   # 关键：解决 Windows 多进程问题
    main()
    