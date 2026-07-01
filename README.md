# Qlib-Trader — Qlib 到 MiniQMT 无人值守实盘交易系统

[![Qlib](https://img.shields.io/badge/Qlib-Microsoft_AI_Quant-0078D4?style=flat-square&logo=microsoft)](https://github.com/microsoft/qlib)
[![QMT](https://img.shields.io/badge/MiniQMT-迅投极速交易-FF6600?style=flat-square)](http://www.thinktrader.net/)
[![Python](https://img.shields.io/badge/Python-3.12.13-blue?style=flat-square&logo=python)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=flat-square&logo=windows)](https://www.microsoft.com/windows)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

![Logo](doc/logo.PNG)

## 项目概述

**Qlib-Trader** 是一个将 Qlib 机器学习量化模型对接 MiniQMT（国金证券/券商极速交易接口）的无人值守实盘交易系统。它实现了"模型预测 → 策略信号 → 自动下单 → 告警通知"的完整闭环，支持崩溃自动重启、健康检查和钉钉实时告警。

### 核心能力

- **模型驱动交易**：Qlib 每日生成预测分数（pred_score.csv），策略根据分数生成买卖信号
- **MiniQMT 实盘对接**：通过 xtquant SDK 直接向券商交易网关发送限价委托
- **生产者-消费者架构**：策略与执行解耦，信号通过优先级队列异步传递
- **无人值守运行**：交易日自动启停、异常自动重启、健康检查守护
- **钉钉实时告警**：交易信号、成交回报、系统异常、每日汇总通过钉钉机器人推送

---

## 系统架构

```
+--------------------------------------------------------+
|                    Windows Task Scheduler              |
|  22:00 数据更新  |  23:00 生成 pred_score.csv           |
+------------------------+-------------------------------+
                         | pred_score.csv
                         v
+--------------------------------------------------------+
|                    qlib_trader                          |
|                                                         |
|  +----------+   +------------+   +-------------------+  |
|  | Strategy |-->| SignalQueue|-->| SignalConsumer    |  |
|  |(Producer)|   |(PriorityQ) |   |   (Executor)      |  |
|  +----------+   +------------+   +---------+---------+  |
|                                             |           |
|  +---------------+  +---------------+       |           |
|  | HealthChecker |  |TradingSched   |       v           |
|  |               |  |               |  +------------+   |
|  +---------------+  +---------------+  |  MiniQMT   |   |
|                                        | (xtquant)  |   |
|  +---------------+  +---------------+  +-----+------+   |
|  | RobustTrader  |  | DingTalkBot   |        |          |
|  |               |  |               |        v          |
|  +---------------+  +---------------+  +------------+   |
|                                        |  券商交易   |   |
|  +---------------+  +---------------+  |  网关       |   |
|  |TradingLogger  |  |TradingMonitor |  +------------+   |
|  +---------------+  +---------------+                   |
+--------------------------------------------------------+
```

### 模块职责

| 模块 | 文件 | 职责 |
|------|------|------|
| 交易引擎 | `trading_engine.py` | 信号队列、生产者/消费者模式、限价委托执行 |
| 策略 | `strategy.py` | TopkDropout 策略，继承 SignalProducer，实现 `_generate_signals()` |
| 告警 | `alert.py` | 钉钉机器人消息推送（文本/Markdown） |
| 日志 | `logger.py` | 分文件日志（主/委托/信号）、交易监控、定时报告 |
| 调度 | `scheduler.py` | 交易日判断、交易时段 9:30-15:00 定时启停 |
| 健康检查 | `health_checker.py` | 连接、心跳、内存三项巡检 |
| 健壮性 | `robust.py` | 崩溃自动重启（可配置重试次数和间隔） |
| 入口 | `main.py` | 加载配置、编排全部组件 |
| 预测脚本 | `script/generate_pred_score.py` | Qlib 模型推理，输出 pred_score.csv |

---

## 实现原理

### 1. 信号流转

```
Qlib pred_score.csv
       |
       v
 Strategy._generate_signals()
       |
       v
 SignalProducer.emit_signal()
       |
       v
 SignalQueue (PriorityQueue)
       |
       v
 SignalConsumer._execute_signal()
       |
       v
 MiniQMT -> Broker -> Exchange
```

### 2. MiniQMT 连接

```python
trader = XtQuantTrader(qmt_path, session_id)
trader.start()
trader.connect()              # 需 QMT 已登录
acc = StockAccount(account_id)
trader.subscribe(acc)
```

### 3. 下单流程

- **买入**：`trader.order_stock(acc, code, STOCK_BUY, volume, FIX_PRICE, price, ...)`
- **卖出**：先查 `query_stock_position()`，`volume = min(signal.volume, pos.can_use_volume)` 防超卖
- **委托类型**：FIX_PRICE（限价单）

### 4. 回调机制

| 回调 | 触发时机 |
|------|----------|
| `on_stock_order(order)` | 委托状态变更（48 未报 → 56 已成） |
| `on_stock_trade(trade)` | 成交回报 |
| `on_order_error(error)` | 委托失败 |
| `on_disconnected()` | 连接断开 |

### 5. 健壮性设计

- **崩溃重启**：RobustTrader 用 try/except 包裹 main()，异常时等待 60 秒重试，上限 10 次
- **健康检查**：每分钟检查连接状态、5 分钟心跳、内存 < 500MB，异常触发钉钉告警
- **时间调度**：仅交易时段运行，9:25 启动、15:05 停止
- **优先级队列**：信号按 priority 排序

### 6. 策略说明（TopkDropout 指数增强）

当前策略 `MyStrategy` 实现的是经典的 **TopkDropout** 日频策略：

- **信号来源**：Qlib 模型预测的 `pred_score.csv`
- **调仓时间**：每个交易日 14:50（T+1 收盘前）
- **持仓数量**：topk=50 只股票（默认以沪深300增强为例）
- **每次卖出**：n_drop=5 只
- **买入金额**：每只 20,000 元
- **无分数持仓处理**：为无预测分数的持仓股赋予最低默认分数，确保排在末尾优先卖出

#### 指数增强策略推荐配置

策略可适配不同的宽基指数增强场景，下表给出各指数对应的推荐参数配置：

| 指数 | 代码 | 建议 Topk | 单票市值 | 建议起始资金 | n_drop | 单票仓位占比 | Topk 占比 |
|------|------|----------|---------|-------------|--------|-------------|-----------|
| 沪深300 | SH000300 | 50 | 2 万 | 100 万 | 5 | 2.00% | 16.67% |
| 中证500 | SH000905 | 80 | 2 万 | 160 万 | 8 | 1.25% | 16.00% |
| 中证800 | SH000906 | 120 | 2 万 | 240 万 | 12 | 0.83% | 15.00% |
| 中证1000 | SH000852 | 150 | 2 万 | 300 万 | 15 | 0.67% | 15.00% |
| 中证2000 | SH932000 | 200 | 2 万 | 400 万 | 20 | 0.50% | 10.00% |
| 中证全指 | SH000985 | 250 | 2 万 | 500 万 | 25 | 0.40% | 5.00% |

**配置说明**：

- **Topk**：持仓股票数量，根据指数成分股数量和流动性调整
- **n_drop**：每次调仓卖出的股票数量，约为 Topk 的 10%，年双边双手率为50倍
- **单票市值**：单只股票的目标持仓市值，固定 2 万元
- **建议起始资金**：基于 `Topk × 单票市值` 计算得到

---

## 环境搭建（完整流程）

### 操作系统

- **Windows 10/11**（MiniQMT 仅支持 Windows）

### Python 环境

```bash
# 0.1 创建 conda 环境
cd ~
conda create -n qlib python=3.12.13 -y
conda activate qlib

# 安装核心依赖
pip install numpy
pip install --upgrade cython

# 安装 Qlib
git clone https://github.com/microsoft/qlib.git && cd qlib
pip install .
cd ..

# 安装 xtquant（MiniQMT SDK）
pip install xtquant
```

### Qlib 数据获取

```bash
# 0.2 下载并解压 Qlib 二进制数据
wget https://github.com/chenditc/investment_data/releases/latest/download/qlib_bin.tar.gz
mkdir -p ~/.qlib/qlib_data/cn_data
tar -zxvf qlib_bin.tar.gz -C ~/.qlib/qlib_data/cn_data --strip-components=1
rm -f qlib_bin.tar.gz
```

> ⚠️ **注意**：数据下载需要科学上网，GitHub 在国内可能无法直接访问。

### 模型训练

```bash
# 0.3 进入 ml 目录，运行训练脚本
cd ml
jupyter notebook
```

训练完成后，在 `ml/mlruns/` 目录下找到 `trained_model` 路径，例如：
```
ml/mlruns/524286176678432781/2628a9cdad6345d691e3de037d546edf/artifacts/trained_model
```

### 配置准备

```bash
# 0.4 准备好配置文件
# 1) MiniQMT 配置 — 确保 QMT 客户端已安装并登录
# 2) 钉钉配置 — 创建钉钉机器人，获取 Webhook 和 Secret
# 3) 模型配置 — 将训练好的模型路径填入 config.yaml 的 model_path
```

---

## 配置文件（格式参考）

编辑 `configs/config.yaml`：

```yaml
# MiniQMT 连接配置
qmt_path: "C:/Users/bytemineur/gjzq/gjzqQMT/userdata_mini"
session_id: 123456
account_id: "888600xxxx"

# 钉钉告警配置
dingtalk_webhook: "https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN"
dingtalk_secret: "SEC_YOUR_SECRET"

# 模型配置
model_path: "C:/Users/bytemineur/Desktop/qlib_trader/ml/mlruns/420455618782912775/40d71f1277b1473a95830c4139f8219a/artifacts/trained_model"
```

**配置项说明**：

| 配置项 | 说明 |
|--------|------|
| `qmt_path` | QMT 用户数据目录（`userdata_mini`），用于 MiniQMT 连接 |
| `session_id` | 会话 ID，任意正整数，用于标识连接 |
| `account_id` | 资金账号，在 QMT 客户端中查看 |
| `dingtalk_webhook` | 钉钉机器人 Webhook 完整 URL |
| `dingtalk_secret` | 钉钉机器人加签密钥（可选，启用后更安全） |
| `model_path` | Qlib 训练好的模型文件路径 |

### 钉钉机器人配置

1. 在钉钉群中添加"自定义机器人"
2. 安全设置选择"加签"，复制 Webhook 地址和 Secret
3. 填入 `configs/config.yaml`

---

## 安装步骤

### 1. 克隆项目

```bash
git clone https://github.com/bytemineur/qlib_trader.git
cd qlib_trader
```

### 2. 创建 conda 环境

```bash
conda create -n qlib python=3.12.13 -y
conda activate qlib
pip install numpy cython pyqlib pyyaml schedule psutil xtquant pandas
```

### 3. 配置 Qlib 数据

```bash
wget -O qlib_bin.tar.gz https://github.com/chenditc/investment_data/releases/latest/download/qlib_bin.tar.gz
mkdir -p ~/.qlib/qlib_data/cn_data
tar -zxvf qlib_bin.tar.gz -C ~/.qlib/qlib_data/cn_data --strip-components=1
rm -f qlib_bin.tar.gz
```

### 4. 训练模型

```bash
cd ml
jupyter notebook
# 记录输出的模型路径，填入 configs/config.yaml 的 model_path
```

### 5. 修改配置

编辑 `configs/config.yaml`，填入真实的 QMT 路径、账号、钉钉 Webhook 和模型路径。

### 6. 启动 MiniQMT

打开国金 QMT 客户端 → 登录 → 确保 MiniQMT 已启用。

### 7. 运行

```bash
conda activate qlib
cd qlib_trader
python qlib_trader/main.py
```

---

## 定时任务（无人值守）

### 数据更新（每日 22:00）

```powershell
schtasks /create /tn "Qlib数据每日更新" /tr "powershell -ExecutionPolicy Bypass -File C:/Users/bytemineur/Desktop/qlib_trader/script/update_qlib_data.ps1" /sc daily /st 22:00
```

查询：
```powershell
schtasks /query /tn "Qlib数据每日更新" /fo LIST /v
```

### 预测分数生成（每日 23:00）

```powershell
schtasks /create /tn "Qlib预测分数生成" /tr "powershell -ExecutionPolicy Bypass -File C:/Users/bytemineur/Desktop/qlib_trader/script/generate_pred_score.ps1" /sc daily /st 23:00
```

查询：
```powershell
schtasks /query /tn "Qlib预测分数生成" /fo LIST /v
```

---

## 项目结构

```
qlib_trader/
├── README.md
├── LICENSE
├── .gitignore
├── configs/
│   ├── config.yaml              # 实际配置（含敏感信息）
│   └── config.yaml.example      # 配置模板
├── qlib_trader/
│   ├── main.py                  # 入口：编排全部组件
│   ├── trading_engine.py        # 交易引擎核心（生产者-消费者）
│   ├── strategy.py              # TopkDropout 策略
│   ├── alert.py                 # 钉钉告警
│   ├── logger.py                # 日志与监控
│   ├── scheduler.py             # 交易时间调度
│   ├── health_checker.py        # 健康检查
│   └── robust.py                # 崩溃重启
├── ml/                          # 模型训练目录
│   ├── workflow_by_code.ipynb   # Jupyter Notebook 训练脚本
│   ├── workflow_by_code.py      # Python 训练脚本
│   ├── workflow_config_lightgbm_Alpha158.yaml  # LightGBM 训练配置
│   ├── pred_score.csv           # 每日预测分数输出
│   └── mlruns/                  # MLflow 实验记录和模型 artifacts
├── script/
│   ├── generate_pred_score.py   # Qlib 预测分数生成
│   ├── generate_pred_score.ps1  # PowerShell 定时任务封装
│   └── update_qlib_data.ps1     # PowerShell 数据更新封装
├── doc/                         # 技术文档
│   ├── main.md
│   ├── trading_engine.md
│   ├── strategy.md
│   ├── alert.md
│   ├── logger.md
│   ├── scheduler.md
│   ├── health_checker.md
│   ├── robust.md
│   ├── generate_pred_score.md
│   └── ml_training.md
├── test/                        # 测试用例
│   ├── __init__.py
│   ├── test_alert.py
│   ├── test_health_checker.py
│   ├── test_logger.py
│   ├── test_robust.py
│   ├── test_scheduler.py
│   ├── test_strategy.py
│   ├── test_trading_engine.py
│   └── test_generate_pred_score.py
└── logs/                        # 运行时日志
    ├── main_YYYYMMDD.log
    ├── trading_YYYYMMDD.log
    ├── orders_YYYYMMDD.log
    ├── signals_YYYYMMDD.log
    ├── generate_pred_score.log
    └── update_qlib_data.log
```

---

## 每日运行流程

```
22:00  数据更新     → 下载最新 Qlib 数据（需科学上网）
23:00  预测生成     → Qlib 推理 → pred_score.csv
09:20  交易启动     → python main.py
         |
09:25   调度器启动   → TradingEngine.start()
09:30   策略运行     → Strategy._generate_signals()
         |
       +- 14:50 调仓 → 读取 pred_score → TopkDropout 计算买卖清单
       |              信号 -> 队列 -> 下单 -> MiniQMT -> 成交
       |              回调 -> 日志 -> 钉钉通知
       +- 健康检查每分钟运行
         |
15:05   调度器停止   → TradingEngine.stop()
15:10   日报推送     → 钉钉汇总
```

---

## 开发指南

### 添加新策略

```python
from trading_engine import SignalProducer, SignalType
import pandas as pd

class MyNewStrategy(SignalProducer):
    def __init__(self, queue, xt_trader, acc, logger, alert):
        super().__init__(queue)
        self.strategy_name = "MyNewStrategy"
        self.xt_trader = xt_trader
        self.acc = acc
        self.logger = logger
        self.alert = alert

    def _generate_signals(self):
        # 读取 pred_score.csv 并生成买卖信号
        self.emit_signal(
            signal_type=SignalType.BUY,
            stock_code="000001.SZ",
            price=10.5, volume=100,
            reason="pred_score > 0.8",
            priority=5
        )
```

在 `main.py` 中注册：
```python
from my_strategy import MyNewStrategy
engine.add_strategy(MyNewStrategy(engine.signal_queue, trader, acc, logger, alert))
```

### 运行测试

```bash
cd qlib_trader
python -m unittest discover -s test -p "test_*.py"
```

---

## 注意事项

1. **仅支持 Windows**：MiniQMT 是 Windows 专有 SDK，无法在 Linux/macOS 上运行
2. **QMT 需提前登录**：运行前确保 QMT 客户端已登录且 MiniQMT 已启用
3. **配置安全**：config.yaml 含敏感信息（账号、Webhook）
4. **日志清理**：日志按天生成不自动清理，建议定期归档
5. **数据更新需科学上网**：Qlib 数据托管在 GitHub，国内用户需配置代理或科学上网
6. **模型路径**：每次重新训练后模型路径会变化，需更新 `config.yaml` 中的 `model_path`

---
## 请作者喝杯咖啡☕️

<div style="display: flex; justify-content: center; align-items: center; gap: 40px; flex-wrap: wrap;">
    <img src="doc/alipay.jpeg" alt="支付宝" style="width: 200px; height: auto;">
    <img src="doc/wechatpay.jpeg" alt="微信支付" style="width: 200px; height: auto;">
</div>
<p style="text-align: center; margin-top: 0px;">
    <span>支付宝</span>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span>微信支付</span>
</p>

## 许可

仅供学习和研究使用。实盘交易有风险，请充分测试后再投入使用。
