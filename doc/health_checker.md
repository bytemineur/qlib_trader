# health_checker.py — 健康检查模块

## 概述

健康检查模块以独立线程方式运行，定期对交易系统进行多项健康指标巡检。当检测到异常时，通过注入的告警函数（如 `TradingAlert.alert_error`）发送通知，确保无人值守场景下故障能被及时发现。

## 类说明

### `HealthChecker`

**构造参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `trading_system` | `object` | 交易系统对象，需暴露 `trader`、`acc` 和 `last_activity` 属性 |
| `alert_func` | `callable` (可选) | 告警回调函数，签名为 `func(error_type, message)` |

**属性**

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `running` | `bool` | `False` | 运行状态标记 |
| `check_interval` | `int` | `60` | 检查间隔（秒），默认每分钟 |

**方法**

| 方法 | 说明 |
|------|------|
| `start()` | 启动健康检查线程（daemon），打印启动信息 |
| `stop()` | 设置 `running=False`，线程将在下一次循环退出 |
| `_check_loop()` | 主循环：每隔 `check_interval` 秒执行一次 `_do_check()` |
| `_do_check()` | 执行全部检查项，汇总 issues 后调用 `alert_func` |

**检查项**

| 方法 | 检查内容 | 判定标准 |
|------|----------|----------|
| `_check_connection()` | 交易连接状态 | 调用 `trader.query_stock_asset(acc)`，无异常即正常 |
| `_check_heartbeat()` | 系统心跳 | `last_activity` 距当前时间 < 300 秒（5分钟） |
| `_check_memory()` | 内存使用 | 当前进程 RSS < 500 MB（需 `psutil`） |

**使用示例**

```python
health = HealthChecker(trading_engine, alert_func=alert.alert_error)
health.start()
# ... 运行 ...
health.stop()
```

## 依赖

- `threading`: 后台线程
- `time`: 时间计算
- `psutil`: 内存检查（`_check_memory` 中延迟导入）

## 注意事项

1. `_check_memory()` 使用 `import psutil` 延迟导入，如果未安装 `psutil`，调用该方法会抛出 `ImportError`
2. 线程为 `daemon=True`，主进程退出时自动终止
3. `_check_connection()` 中的 `trader.query_stock_asset` 在没有实际 QMT 环境时会失败，测试时需 mock
