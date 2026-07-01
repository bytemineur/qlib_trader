# ml_training.md — 模型训练指南

## 概述

Qlib-Trader 的交易信号来源于 Qlib 机器学习模型的每日预测。本章介绍如何训练一个 LightGBM 模型（基于 Alpha158 因子），并将其用于实盘预测。

模型训练通过 `ml/workflow_by_code.py`（或 `ml/workflow_by_code.ipynb`）脚本完成，训练完成后将模型文件路径填入 `configs/config.yaml` 的 `model_path` 配置项。

---

## 前置条件

- Python 3.12.13 + conda 环境 `qlib`
- Qlib 已安装（`pip install qlib`）
- Qlib 二进制数据已下载至 `~/.qlib/qlib_data/cn_data/`

---

## 训练流程

### 1. 进入训练目录

```bash
conda activate qlib
cd C:/Users/bytemineur/Desktop/qlib_trader/ml
```

### 2. 执行训练脚本

**方式一：Python 脚本（推荐）**

```bash
python workflow_by_code.py
```

**方式二：Jupyter Notebook**

```bash
jupyter notebook workflow_by_code.ipynb
```

### 3. 训练流程详解

训练脚本 `workflow_by_code.py` 的执行流程如下：

```
1. 初始化 Qlib（provider_uri 指向 ~/.qlib/qlib_data/cn_data）
2. 初始化模型（CSI300_GBDT_TASK["model"] — LightGBM）
3. 初始化数据集（CSI300_GBDT_TASK["dataset"] — 沪深300成分股 + Alpha158因子）
4. 数据处理（dataset.prepare("train")）
5. 启动 MLflow 实验
6. 模型训练（model.fit(dataset)）
7. 保存模型 artifacts
8. 信号记录（SignalRecord）— 生成预测分数
9. 信号分析（SigAnaRecord）
10. 回测分析（PortAnaRecord）— TopkDropout 策略回测
```

### 4. 训练配置说明

训练使用 Qlib 内置的 `CSI300_GBDT_TASK` 配置：

| 配置项 | 值 | 说明 |
|--------|-----|------|
| 模型 | LightGBM (GBDT) | 梯度提升决策树 |
| 数据集 | 沪深300成分股 | 股票池 |
| 因子 | Alpha158 | 158个标准化因子 |
| 训练区间 | 2017-01-01 ~ 2020-08-01 | 回测区间 |
| 回测策略 | TopkDropoutStrategy | topk=50, n_drop=5 |
| 初始资金 | 100,000,000 | 1亿 |
| 手续费 | 买入0.05%, 卖出0.15% | 双边 |
| 滑点 | 收盘价成交 | deal_price=close |

---

## 获取模型路径

训练完成后，模型保存在 MLflow 的实验目录下：

```
ml/mlruns/
├── <experiment_id>/
│   ├── <run_id>/
│   │   └── artifacts/
│   │       └── trained_model    ← 模型文件
│   └── meta.yaml
```

示例路径：
```
C:/Users/bytemineur/Desktop/qlib_trader/ml/mlruns/420455618782912775/40d71f1277b1473a95830c4139f8219a/artifacts/trained_model
```

将此完整路径填入 `configs/config.yaml` 的 `model_path` 字段。

---

## 模型更新流程

建议每月或每季度重新训练模型以适应市场变化：

1. 更新 Qlib 数据：`python script/update_qlib_data.ps1`（或手动下载最新数据）
2. 重新训练：`cd ml && python workflow_by_code.py`
3. 更新配置：将新的 `model_path` 填入 `configs/config.yaml`
4. 验证预测：`python script/generate_pred_score.py` 检查输出

---

## 依赖

- `qlib` 核心框架（含 LightGBM、MLflow）
- `numpy`、`pandas`、`cython`

## 注意事项

1. **模型路径包含 run_id**：每次训练会生成不同的 run_id，需更新配置
2. **数据需要科学上网**：Qlib 数据托管在 GitHub，国内用户需配置代理
3. **MLflow 实验目录**：`ml/mlruns/` 会随训练累积，建议定期清理旧实验
4. **特征一致性**：确保 `generate_pred_score.py` 使用与训练时相同的因子处理器（Alpha158）
5. **模型格式**：训练输出为 `.pkl` 格式的 pickle 文件，通过 `pickle.load()` 加载
