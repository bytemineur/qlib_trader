# Qlib-Trader — Qlib 到 MiniQMT 无人值守实盘交易系统

[![Python](https://img.shields.io/badge/Python-3.12-blue?style=flat-square&logo=python)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=flat-square&logo=windows)](https://www.microsoft.com/windows)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

![Logo](doc/logo.PNG)

**Qlib-Trader** 将 Qlib 机器学习量化模型对接 MiniQMT（国金证券极速交易接口），实现"模型预测 → 策略信号 → 自动下单 → 钉钉告警"的完整闭环，支持崩溃自动重启和健康检查。

---

## 系统架构

```
┌──────────────────────────────────────────────────────────────┐
│  Windows Task Scheduler                                       │
│  20:00 数据更新  |  23:00 生成 pred_score.csv                  │
├──────────────────────────────────────────────────────────────┤
│  qlib_trader                                                   │
│                                                                │
│  ┌──────────┐   ┌────────────┐   ┌──────────────────────────┐ │
│  │ Strategy  │──▶│ SignalQueue│──▶│ SignalConsumer (执行器)   │ │
│  │ (Producer)│   │ (PriorityQ)│   └───────────┬──────────────┘ │
│  └──────────┘   └────────────┘               │                │
│                                               ▼                │
│  ┌─────────────┐  ┌─────────────┐    ┌──────────────┐         │
│  │HealthChecker│  │TradingSched │    │    MiniQMT    │         │
│  └─────────────┘  └─────────────┘    │   (xtquant)   │         │
│                                       └──────┬───────┘         │
│  ┌─────────────┐  ┌─────────────┐           │                 │
│  │RobustTrader │  │ DingTalkBot │           ▼                 │
│  └─────────────┘  └─────────────┘    ┌──────────────┐         │
│                                       │  券商交易网关  │         │
│                                       └──────────────┘         │
└──────────────────────────────────────────────────────────────┘
```

---

## 模块说明

| 文件 | 职责 |
|------|------|
| `main.py` | 入口：加载配置、编排全部组件 |
| `trading_engine.py` | 交易引擎核心：优先级信号队列、生产者/消费者模式、限价委托 |
| `strategy.py` | TopkDropout 策略：读取 pred_score.csv，计算买卖清单 |
| `alert.py` | 钉钉机器人：文本/Markdown 消息推送 |
| `logger.py` | 日志系统：分文件日志（主/委托/信号）、交易监控、定时报告 |
| `scheduler.py` | 交易时间调度：交易日判断、9:25 启 / 15:05 停 / 15:10 日报 |
| `health_checker.py` | 健康检查：连接、5 分钟心跳、内存 < 500MB |
| `robust.py` | 崩溃重启：最多重试 10 次，间隔 60 秒 |
| `script/generate_pred_score.py` | 加载 Qlib 模型 → 推理 → 输出 pred_score.csv |
| `script/update_qlib_data.ps1` | 数据更新（CSV → Qlib 二进制） |
| `script/data_collector/` | 数据采集三步脚本（股票列表 → 行情下载 → 转 Qlib 格式） |

---

## 策略

当前策略 `MyStrategy` 实现 **TopkDropout 日频策略（中证全指指数增强）**：

- **信号来源**：Qlib 模型每日预测的 `pred_score.csv`
- **调仓时间**：每个交易日 14:50
- **持仓数量**：topk = 250 只
- **每次卖出**：n_drop = 25 只
- **买入金额**：每只 20,000 元
- **默认分数**：无预测分数的持仓股赋予最低分数，确保优先卖出
- **科创板支持**：688 开头股票交易单位为 200 股，其余为 100 股
- **停牌/涨停保护**：卖一价为 0 时跳过买入

---

## 每日运行流程

```
20:00  数据更新     → 数据下载 → 转 Qlib 二进制
23:00  预测生成     → Qlib 推理 → ml/pred_score.csv
09:20  交易启动     → python qlib_trader/main.py
09:25  调度器启动   → TradingEngine.start()
09:30  策略就绪     → Strategy._generate_signals() 每秒轮询
        |
        +- 14:50 调仓 → 读取 pred_score → 计算买卖清单 → 下单 → MiniQMT
        |              回调 → 日志 → 钉钉通知
        +- 每分钟健康检查
        |
15:05  调度器停止   → TradingEngine.stop()
15:10  日报推送     → 钉钉 Markdown 汇总
```

---

## 环境搭建

### 前提

- Windows 10/11（MiniQMT 仅支持 Windows）
- QMT 客户端已安装并登录

### 安装

```bash
# 1. 创建 conda 环境
conda create -n qlib python=3.12.13 -y
conda activate qlib

# 2. 安装依赖
pip install numpy cython pyqlib pyyaml schedule psutil xtquant pandas chinese-calendar

# 3. Qlib 数据
cd script
.\update_qlib_data.ps1

# 4. 训练模型
cd ml
jupyter notebook
# 记录输出的模型路径
```

### 配置

复制 `configs/config.yaml.example` 为 `configs/config.yaml`，填入实际配置：

```yaml
qmt_path: "C:/Users/xxx/gjzq/gjzqQMT/userdata_mini"
session_id: 123456
account_id: "888600xxxx"
dingtalk_webhook: "https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN"
dingtalk_secret: "SEC_YOUR_SECRET"
model_path: "C:/Users/xxx/Desktop/qlib_trader/ml/mlruns/xxx/artifacts/trained_model"
```

### 运行

```bash
python qlib_trader/main.py
```

---

## 定时任务

```powershell
cd script
.\CreateScheduledTasks.ps1 # 数据更新（每日 20:00） / 预测分数生成（每日 23:00）
```

---

## 开发指南

### 添加新策略

```python
from trading_engine import SignalProducer, SignalType

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
---

## 项目结构

```
qlib_trader/
├── qlib_trader/                  # 交易系统核心
│   ├── main.py                   # 入口
│   ├── trading_engine.py         # 交易引擎
│   ├── strategy.py               # 策略
│   ├── alert.py                  # 钉钉告警
│   ├── logger.py                 # 日志与监控
│   ├── scheduler.py              # 时间调度
│   ├── health_checker.py         # 健康检查
│   └── robust.py                 # 崩溃重启
├── ml/                           # 模型训练
│   ├── workflow_by_code.py       # 训练脚本
│   ├── pred_score.csv            # 每日预测输出
│   └── mlruns/                   # MLflow artifacts
├── script/
│   ├── CreateScheduledTasks.ps1  # 定时任务脚本
│   ├── generate_pred_score.py    # 预测分数生成
│   ├── generate_pred_score.ps1   # PowerShell 封装
│   ├── update_qlib_data.ps1      # 数据更新封装
│   └── data_collector/           # 数据采集脚本
├── configs/
│   ├── config.yaml               # 实际配置（不入库）
│   └── config.yaml.example       # 配置模板
└── logs/                         # 运行时日志
```

---

## 注意事项

1. **仅支持 Windows**：MiniQMT SDK 为 Windows 专有
2. **QMT 需提前登录**：运行前确保 QMT 客户端已登录且 MiniQMT 已启用
3. **配置文件不入库**：`config.yaml` 含敏感信息，已在 `.gitignore` 中排除
4. **日志不自动清理**：按天生成，建议定期归档
5. **模型路径需更新**：重新训练后模型路径变化，需更新 `config.yaml`

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
