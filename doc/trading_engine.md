# trading_engine.py — 交易引擎核心模块

## 概述

交易引擎是系统的核心模块，采用**生产者-消费者**模式解耦信号生成与交易执行。策略（生产者）将交易信号放入优先级队列，执行器（消费者）从队列取出信号并通过 MiniQMT 下单。

## 架构图

```
+--------------+    +----------------+    +--------------+
|  Strategy A  |--->|                |--->|              |
|  (Producer)  |    |  SignalQueue   |    |  Consumer    |---> MiniQMT
|  Strategy B  |--->| (PriorityQueue)|    | (Executor)   |
+--------------+    +----------------+    +--------------+
                           |
                           v
                    +--------------+
                    |   History    |
                    |  (deque 1K)  |
                    +--------------+
```

---

## 枚举与数据类

### `SignalType(Enum)`

| 成员 | 值 | 说明 |
|------|-----|------|
| `BUY` | `1` | 买入信号 |
| `SELL` | `2` | 卖出信号 |

### `TradeSignal`

交易信号数据类，支持优先级队列排序。

**字段**

| 字段 | 类型 | 说明 |
|------|------|------|
| `signal_id` | `str` | UUID前8位 |
| `signal_type` | `SignalType` | 买卖方向 |
| `stock_code` | `str` | 股票代码 |
| `price` | `float` | 委托价格 |
| `volume` | `int` | 委托数量(股) |
| `strategy` | `str` | 来源策略 |
| `reason` | `str` | 信号原因 |
| `timestamp` | `datetime` | 生成时间 |
| `priority` | `int` | 优先级(越大越优先) |

---

## 类说明

### `SignalQueue`

包装 `PriorityQueue`，增加历史记录。

| 方法 | 说明 |
|------|------|
| `put(signal)` | 入队并记录历史 |
| `get(block, timeout)` | 阻塞出队 |
| `get_nowait()` | 非阻塞出队 |
| `qsize()` | 队列长度 |
| `empty()` | 是否为空 |
| `clear()` | 清空队列 |
| `get_history(n=10)` | 获取最近n条历史 |

### `SignalProducer`

信号生产者基类，在独立线程中循环调用 `_generate_signals()`。

| 方法 | 说明 |
|------|------|
| `start()` | 启动 daemon 线程 |
| `stop()` | 停止运行 |
| `emit_signal(...)` | 构造 `TradeSignal` 并入队 |

### `SignalConsumer`

信号消费者，从队列取信号执行交易。

| 属性 | 说明 |
|------|------|
| `executed_count` | 成功执行数 |
| `failed_count` | 失败执行数 |

**卖出风控**: 检查 `can_use_volume`，`volume = min(signal.volume, pos.can_use_volume)`

### `TradingEngine`

统一管理生产者和消费者。

| 方法 | 说明 |
|------|------|
| `add_strategy(producer)` | 添加策略 |
| `start()` | 先启动consumer，后启动producer |
| `stop()` | 先停止producer，后停止consumer |
| `get_stats()` | 返回 `{queue_size, executed, failed}` |

## 依赖

- `threading`, `time`, `uuid`, `enum`, `dataclasses`, `datetime`, `typing`
- `queue.PriorityQueue`, `collections.deque`
- `xtquant.xtconstant`

## 注意事项

1. 优先级队列高优先级先出（`__lt__` 已调整）
2. 历史记录上限1000条
3. 消费者 `get(timeout=1)` 避免忙等
4. 卖出有持仓检查和风控
