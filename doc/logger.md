# logger.py — 日志与监控模块

## 概述

日志与监控模块是交易系统的"记录仪"和"仪表盘"。它将日志按用途拆分（主日志、委托日志、信号日志），并通过 MiniQMT 回调实时记录委托状态变化；同时提供交易监控器统计运行指标，并由定时报告调度器周期性输出。

---

## 函数

### `setup_logger(name='trading', log_dir='logs')`

创建并配置一个带日期的日志器。

**参数**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | `str` | `'trading'` | 日志器名称 |
| `log_dir` | `str` | `'logs'` | 日志文件目录（不存在则自动创建） |

**返回值**: `logging.Logger` — 配置好的日志器实例。

**日志输出规则**

| 输出目标 | 级别 | 格式 |
|----------|------|------|
| 文件 (`{name}_{YYYYMMDD}.log`) | DEBUG 及以上 | `时间 | 级别 | 名称 | 消息` |
| 控制台 (`stdout`) | INFO 及以上 | 同上 |

---

## 类说明

### `TradingLogger`

交易日志封装，内部持有三个独立的日志器实例，分别记录不同维度的信息。

**构造参数**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `log_dir` | `str` | `'logs'` | 日志目录 |

**属性**

| 属性 | 类型 | 说明 |
|------|------|------|
| `logger` | `Logger` | 主日志器（name='trading'） |
| `order_logger` | `Logger` | 委托日志器（name='orders'） |
| `signal_logger` | `Logger` | 信号日志器（name='signals'） |

**方法**

| 方法 | 参数 | 说明 |
|------|------|------|
| `log_signal(strategy, stock_code, signal_type, reason)` | 策略、股票、方向、原因 | 记录交易信号到 signals.log |
| `log_order(order_id, stock_code, direction, volume, price, status)` | 委托ID、股票、方向、数量、价格、状态 | 记录委托到 orders.log |
| `log_trade(order_id, stock_code, volume, price, amount)` | 委托ID、股票、数量、价格、金额 | 记录成交到 orders.log |
| `log_error(error_type, message, detail)` | 错误类型、信息、详情(可选) | 记录错误到 trading.log |
| `log_position(positions)` | 持仓列表 | 以格式化快照写入 trading.log |

**使用示例**

```python
tl = TradingLogger()
tl.log_signal("双均线", "000001.SZ", "buy", "金叉")
tl.log_order("ORD123", "000001.SZ", "买入", 100, 10.5, "已报")
tl.log_trade("ORD123", "000001.SZ", 100, 10.5, 1050.0)
tl.log_error("NETWORK", "连接超时", detail="3次重试失败")
```

---

### `LoggingCallback(XtQuantTraderCallback)`

继承 MiniQMT 回调基类，将回调事件转化为结构化日志。

**构造参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `trading_logger` | `TradingLogger` | 日志封装实例 |

**回调方法**

| 回调 | 触发时机 | 日志动作 |
|------|----------|----------|
| `on_disconnected()` | 与 MiniQMT 断开连接 | 记录 CONNECTION 错误 |
| `on_stock_order(order)` | 委托状态变更 | 记录委托（含状态映射） |
| `on_stock_trade(trade)` | 成交回报 | 记录成交明细 |
| `on_order_error(error)` | 委托失败 | 记录 ORDER_ERROR 及详情 |
| `on_cancel_error(error)` | 撤单失败 | 记录 CANCEL_ERROR 及详情 |

**委托状态码映射表**

| 状态码 | 含义 | | 状态码 | 含义 |
|--------|------|-|--------|------|
| 48 | 未报 | | 53 | 部撤 |
| 49 | 待报 | | 54 | 已撤 |
| 50 | 已报 | | 55 | 部成 |
| 51 | 已报待撤 | | 56 | 已成 |
| 52 | 部成待撤 | | 57 | 废单 |

---

### `TradingMonitor`

交易监控器，实时统计信号、委托、成交、错误的数量和金额，支持分股票维度聚合。

**属性**

| 属性 | 类型 | 说明 |
|------|------|------|
| `start_time` | `float` | 系统启动时间戳 |
| `metrics` | `dict` | 全局指标字典 |
| `stock_metrics` | `defaultdict` | 分股票指标 |

**metrics 字段**

| 字段 | 说明 |
|------|------|
| `orders_total` | 委托总数 |
| `orders_success` | 成功委托数 |
| `orders_failed` | 失败委托数 |
| `trades_total` | 成交笔数 |
| `trades_amount` | 成交总金额 |
| `signals_total` | 信号总数 |
| `errors_total` | 错误次数 |

**方法**

| 方法 | 参数 | 说明 |
|------|------|------|
| `on_signal(stock_code)` | 股票代码 | 信号计数 +1 |
| `on_order(stock_code, success)` | 股票代码、是否成功 | 委托计数 +1 |
| `on_trade(stock_code, amount)` | 股票代码、成交金额 | 成交计数和金额累加 |
| `on_error()` | — | 错误计数 +1 |
| `get_report()` | — | 返回格式化监控报告 |
| `print_report()` | — | 直接打印报告 |

---

### `ReportScheduler`

定时报告调度器，使用 `schedule` 库实现周期性报告输出。

**构造参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `monitor` | `TradingMonitor` | 监控器实例 |
| `logger` | `Logger` | 日志器（用于写入报告） |

**方法**

| 方法 | 说明 |
|------|------|
| `start()` | 启动调度线程（每整点报告 + 每日15:05收盘汇总） |
| `stop()` | 停止调度 |
| `_hourly_report()` | 输出小时报告 |
| `_daily_report()` | 输出每日汇总报告 |

---

## 依赖

- `os`, `time`, `threading`: 标准库
- `schedule`: 定时任务调度
- `logging`: Python 标准日志库
- `collections.defaultdict`: 分股票聚合
- `xtquant.xttrader.XtQuantTraderCallback`: MiniQMT 回调基类

## 注意事项

1. 日志文件按天命名，同一天追加写入，不会自动清理，生产环境建议配合 logrotate
2. `LoggingCallback` 依赖 MiniQMT 环境，独立测试需 mock 回调事件
3. `TradingMonitor` 的成功率计算用 `max(1, total)` 避免除零
