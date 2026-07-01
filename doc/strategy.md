# strategy.py — 策略模块

## 概述

策略模块定义具体的交易策略逻辑。每个策略继承自 `trading_engine.SignalProducer` 基类，通过重写 `_generate_signals()` 方法实现自定义的信号生成逻辑。

当前 `MyStrategy` 实现的是 **TopkDropout 沪深300指数增强** 日频策略：T日收盘后生成预测分数，T+1日收盘前 14:50 调仓。

## 类说明

### `MyStrategy(SignalProducer)`

TopkDropout 策略，继承自 `SignalProducer`。

**构造参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `queue` | `SignalQueue` | 信号队列，由 `TradingEngine` 传入 |
| `xt_trader` | `XtQuantTrader` | MiniQMT 交易接口，用于查询持仓和行情 |
| `acc` | `StockAccount` | 资金账户 |
| `logger` | `Logger` | 日志记录器 |
| `alert` | `TradingAlert` | 钉钉告警服务 |

**属性**

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `strategy_name` | `str` | `"TopkDropoutStrategy_沪深300指数增强"` | 策略名称 |
| `topk` | `int` | `50` | 持仓数量 |
| `n_drop` | `int` | `5` | 每次调仓卖出数量 |
| `cash` | `int` | `20_000` | 每只股票买入金额（元） |
| `last_rebalance_date` | `date` | `None` | 上次调仓日期（防重复触发） |

**方法**

| 方法 | 说明 |
|------|------|
| `_generate_signals()` | 信号生成逻辑：14:50 读取 pred_score.csv，计算买卖清单，生成交易信号 |
| `_get_dropout_trade_list()` | TopkDropout 核心算法：根据预测分数、当前持仓计算买入/卖出列表 |

## 信号生成流程

```
_generate_signals() [每分钟调用]
  ├─ 检查时间: 14:50-14:51 且当日未调仓
  │
  ├─ 1. 读取 ml/pred_score.csv
  │   └─ convert_code(): SH600000 → 600000.SH
  │
  ├─ 2. 查询当前持仓 (xt_trader.query_stock_positions)
  │
  ├─ 3. _get_dropout_trade_list() 计算买卖清单
  │   ├─ 清理预测分数（dropna）
  │   ├─ 无分数持仓 → 赋予最低默认分
  │   ├─ 候选买入池 → 有分数且未持有的股票
  │   ├─ 合并排序 → 按分数降序排列
  │   ├─ 尾部 n_drop 只 → 卖出清单（仅限原持仓）
  │   └─ 补仓 → 买入清单
  │
  ├─ 4. 获取实时行情 (xtdata.get_full_tick)
  │
  ├─ 5. 生成 SELL 信号（优先级=1，优先执行）
  │   └─ volume = 当前持仓量
  │
  ├─ 6. 生成 BUY 信号（优先级=0）
  │   └─ volume = floor((cash / price) / 100) * 100  # 按100股整数倍
  │
  └─ 7. 记录 last_rebalance_date
```

## TopkDropout 算法 (`_get_dropout_trade_list`)

```python
def _get_dropout_trade_list(pred_score, current_holdings, topk, n_drop):
    """
    支持持仓股无预测分数的 TopkDropout 策略

    Args:
        pred_score: Series, index=stock_code, value=prediction_score
        current_holdings: List[str], 当前持仓股票列表
        topk: int, 目标持仓数量
        n_drop: int, 每次调仓卖出的股票数量

    Returns:
        (buy_list, sell_list): 买入和卖出的股票代码列表
    """
```

**核心逻辑**:

1. 为无预测分数的持仓股赋予极低默认分数（`pred_score.min() - 1`），确保排在末尾优先卖出
2. 候选买入池仅包含有分数且未持有的股票
3. 合并当前持仓和候选买入，按分数降序排列
4. 从组合尾部取出 n_drop 只，仅卖出原持仓中的股票
5. 根据卖出数量和目标仓位计算买入数量

## 使用示例

```python
from strategy import MyStrategy

# 在 main.py 中注册
strategy = MyStrategy(
    queue=engine.signal_queue,
    xt_trader=trader,
    acc=acc,
    logger=logger,
    alert=alert
)
engine.add_strategy(strategy)
```

## 依赖

- `pandas`: 读取 pred_score.csv 和数据处理
- `xtquant.xtdata`: 获取实时行情（`get_full_tick`）
- `trading_engine`: 基类 `SignalProducer`, `SignalType`

## 注意事项

1. **调仓时间固定在 14:50**：这是 Qlib 日频策略的标准调仓时间（T+1 收盘前）
2. **每日仅调仓一次**：通过 `last_rebalance_date` 防止同一分钟重复触发
3. **买入量按 100 股整数倍**：A 股最小交易单位为 100 股（1 手）
4. **卖出优先执行**：SELL 信号 priority=1 > BUY 信号 priority=0，确保先卖后买
5. **无分数持仓可卖出**：持仓但当天无预测分数的股票会被赋予最低分，优先卖出
6. **策略名称含中文**：用于日志和告警标识
