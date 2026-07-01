# robust.py — 健壮性保障模块

## 概述

`RobustTrader` 为交易主函数提供崩溃自动重启机制，确保无人值守场景下偶发异常（如网络闪断、API 超时）不会导致系统永久停止。它通过 `try/except` 包裹主函数，在异常时等待指定间隔后重试，达到最大次数后退出并告警。

## 类说明

### `RobustTrader`

**构造参数**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `trader_func` | `callable` | (必填) | 交易主函数（通常为 `main`） |
| `max_retries` | `int` | `10` | 最大重试次数 |
| `retry_interval` | `int` | `60` | 重试间隔（秒） |

**属性**

| 属性 | 类型 | 说明 |
|------|------|------|
| `retry_count` | `int` | 当前已重试次数 |

**方法**

| 方法 | 说明 |
|------|------|
| `run()` | 进入重试循环，调用 `trader_func` |
| `_send_alert(message)` | 发送告警（当前为 print） |

**执行逻辑**

```
while retry_count < max_retries:
    try:
        执行 trader_func()
        break  # 正常结束
    except KeyboardInterrupt:
        重新抛出
    except Exception:
        retry_count += 1
        打印错误和堆栈
        if retry_count < max_retries:
            等待 retry_interval 秒后重试
        else:
            发送告警并 sys.exit(1)
```

**使用示例**

```python
robust_trader = RobustTrader(main, max_retries=10, retry_interval=60)
robust_trader.run()
```

## 依赖

- `sys`: 退出
- `time`: 重试等待
- `traceback`: 堆栈打印
- `datetime`: 时间戳

## 注意事项

1. `KeyboardInterrupt` 会被 `raise` 重新抛出，确保 Ctrl+C 能立即退出
2. `trader_func` 正常 `return` 不会触发重试
3. `_send_alert` 当前为 `print`，生产环境建议接入 Webhook
4. `sys.exit(1)` 以非零返回码退出，便于外部监控
