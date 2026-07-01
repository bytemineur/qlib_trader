# scheduler.py — 交易时间调度模块

## 概述

交易时间调度器负责判断当前是否处于交易日和交易时段，并按预设时间点自动启动/停止交易系统、发送每日报告。

## 类说明

### `TradingScheduler`

**构造参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `trading_system` | `object` | 交易系统对象，需实现 `start()`, `stop()`, `send_daily_report()` |

**属性**

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `running` | `bool` | `False` | 运行状态 |

**方法**

| 方法 | 说明 |
|------|------|
| `is_trading_day()` | 判断是否为交易日（当前仅过滤周末） |
| `is_trading_time()` | 判断是否在交易时段（9:30-11:30, 13:00-15:00） |
| `start()` | 注册定时任务并启动调度线程 |
| `stop()` | 停止调度 |
| `_start_trading()` | 调用 `trading_system.start()` |
| `_stop_trading()` | 调用 `trading_system.stop()` |
| `_send_daily_report()` | 调用 `trading_system.send_daily_report()` |

**定时任务时间表**

| 时间 | 任务 | 说明 |
|------|------|------|
| 09:25 | `_start_trading()` | 提前5分钟启动 |
| 15:05 | `_stop_trading()` | 延后5分钟停止 |
| 15:10 | `_send_daily_report()` | 收盘后发送日报 |

**交易时段**

| 时段 | 时间 |
|------|------|
| 上午 | 09:30 – 11:30 |
| 下午 | 13:00 – 15:00 |

**使用示例**

```python
scheduler = TradingScheduler(trading_engine)
scheduler.start()
# ... 运行 ...
scheduler.stop()
```

## 依赖

- `datetime`: 日期时间判断
- `time`: sleep
- `schedule`: 定时任务
- `threading`: 后台线程

## 注意事项

1. **节假日判断缺失**: 当前仅过滤周末，法定节假日会被视为交易日
2. **时区**: 使用本地时间，默认东八区
3. **重复调用**: `_start_trading()` 在非交易日也会触发，内部有二次校验
