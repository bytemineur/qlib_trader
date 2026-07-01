# generate_pred_score.py — 预测分数生成脚本

## 概述

利用 Qlib 框架加载训练好的 ML 模型，对最新交易日推理预测，生成 `pred_score.csv` 供策略使用。

该脚本由 Windows 定时任务在每日 23:00 自动触发执行。

## 文件位置

`script/generate_pred_score.py`

## 前置条件

- Qlib 环境（`conda activate qlib`）
- 模型文件存在（`config.yaml` 中 `model_path` 指向的 .pkl 文件）
- Qlib 数据已更新至最新

## 执行流程

```
main()
  ├─ 1. pickle.load 加载模型（从 config.yaml 的 model_path 读取）
  ├─ 2. qlib.init() 初始化 Qlib
  ├─ 3. D.calendar() 获取最新交易日
  ├─ 4. Alpha158 特征处理器 (前90天数据)
  ├─ 5. DatasetH 数据集
  ├─ 6. model.predict() 推理
  └─ 7. pred_score.csv 输出至 ml/ 目录
```

### 详细步骤

#### 1. 加载模型

```python
model_path = CONFIG['model_path']
with open(model_path, "rb") as f:
    model = pickle.load(f)
```

模型路径从 `configs/config.yaml` 的 `model_path` 配置项读取，支持绝对路径。

#### 2. 初始化 Qlib

```python
qlib.init()  # 在 main() 内部调用，避免子进程重复初始化（Windows 多进程安全）
```

#### 3. 获取最新交易日

```python
calendar = D.calendar(freq="day")
latest_day = calendar[-1]
```

#### 4. 准备特征数据

```python
handler = Alpha158(
    instruments="csi300",       # 沪深300成分股
    start_time=calendar[-90],   # 取前90天作为数据起始
    end_time=latest_day,
    infer_processors=[],        # 推理时不要拟合任何处理器
)
```

#### 5. 构造数据集

```python
dataset = DatasetH(handler, segments={"all": (start_time, end_time)})
```

#### 6. 模型推理

```python
pred_score = model.predict(dataset, segment="all")
latest_pred = pred_score.xs(latest_day, level=0)
```

#### 7. 保存预测结果

```python
csv_path = Path(__file__).parent.parent / 'ml' / 'pred_score.csv'
latest_pred.to_csv(csv_path, index=True, encoding="utf-8-sig")
```

## 关键参数

| 参数 | 值 | 说明 |
|------|-----|------|
| `instruments` | `"csi300"` | 沪深300成分股 |
| `start_time` | 最新日前90天 | 特征窗口 |
| `infer_processors` | `[]` | 避免推理时数据泄漏 |
| `model_path` | 来自 config.yaml | 训练好的模型文件路径 |

## 输出

`ml/pred_score.csv` — 两列：

| 列名 | 说明 |
|------|------|
| `instrument` | 股票代码（如 SH600000） |
| `score` | 预测分数（越高越好） |

编码为 `utf-8-sig`，兼容 Excel 直接打开。

## 定时任务配置

通过 Windows Task Scheduler 每日 23:00 自动执行：

```powershell
schtasks /create /tn "Qlib预测分数生成" /tr "powershell -ExecutionPolicy Bypass -File C:/Users/bytemineur/Desktop/qlib_trader/script/generate_pred_score.ps1" /sc daily /st 23:00
```

PowerShell 封装脚本 `generate_pred_score.ps1`：

```powershell
conda activate qlib
cd C:/Users/bytemineur/Desktop/qlib_trader/script
python generate_pred_score.py
```

## 入口点

```python
if __name__ == '__main__':
    mp.freeze_support()  # Windows 多进程兼容（必须！）
    main()
```

## 依赖

- `pickle`：模型加载
- `multiprocessing`：`freeze_support()` Windows 兼容
- `qlib` 核心框架：数据、因子、数据集、模型推理

## 注意事项

1. **模型路径从配置文件读取**：无需硬编码，通过 `config.yaml` 的 `model_path` 配置
2. **需要最新 Qlib 数据**：数据需在每日 22:00 先完成更新（由 `update_qlib_data.ps1` 执行）
3. **`qlib.init()` 在 `main()` 内调用**：Windows 多进程安全要求，避免在模块级别调用
4. **CSV 使用 `utf-8-sig` 编码**：兼容 Excel 打开不乱码
5. **`infer_processors=[]`**：推理时不能拟合处理器，否则会导致数据泄漏
6. **`mp.freeze_support()`**：Windows 平台必须调用，否则子进程可能重复执行
