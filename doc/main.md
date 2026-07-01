# main.py — 程序入口

## 概述

`main.py` 是整个无人值守交易系统的启动入口。它负责加载配置、初始化所有子系统组件（日志、告警、交易连接、引擎、调度、健康检查），并将它们编排为一个完整的交易服务。入口使用 `RobustTrader` 包裹主函数，实现崩溃自动重启。

## 架构流程

```
main()
  ├─ 1. 加载配置 (load_config)
  ├─ 2. 启动定时报告 (ReportScheduler)
  ├─ 3. 初始化告警 (DingTalkBot → TradingAlert)
  ├─ 4. 建立交易连接 (XtQuantTrader + StockAccount)
  ├─ 5. 注册回调 (LoggingCallback)
  ├─ 6. 启动交易引擎 (TradingEngine + MyStrategy)
  ├─ 7. 启动时间调度 (TradingScheduler)
  ├─ 8. 启动健康检查 (HealthChecker)
  └─ 9. 主循环 (每分钟更新 last_activity)
```

**停止流程**（`KeyboardInterrupt` 或异常）:
```
finally:
  scheduler.stop() → health.stop() → engine.stop() → trader.stop() → rs.stop()
```

## 函数

### `load_config()`

加载 `configs/config.yaml` 配置文件。

- **配置文件路径**: `{项目根目录}/configs/config.yaml`
- **抛出**: `FileNotFoundError` — 配置文件不存在时
- **返回**: `dict` — 解析后的配置字典

**配置结构**:
```yaml
qmt_path: "C:/Users/bytemineur/gjzq/gjzqQMT/userdata_mini"
session_id: 123456
account_id: "8886008687"
dingtalk_webhook: "https://oapi.dingtalk.com/robot/send?..."
dingtalk_secret: "SEC..."
model_path: "C:/Users/bytemineur/Desktop/qlib_trader/ml/mlruns/.../trained_model"
```

**配置项说明**:

| 配置项 | 类型 | 说明 |
|--------|------|------|
| `qmt_path` | `str` | QMT 用户数据目录（`userdata_mini`） |
| `session_id` | `int` | 会话 ID，用于标识交易连接 |
| `account_id` | `str` | 资金账号 |
| `dingtalk_webhook` | `str` | 钉钉机器人 Webhook 完整 URL |
| `dingtalk_secret` | `str` | 钉钉机器人加签密钥 |
| `model_path` | `str` | 训练好的模型文件路径（.pkl），供 `generate_pred_score.py` 使用 |

### `main()`

主函数，无参数，不返回值。

**启动顺序**:
1. 打印系统启动横幅（含时间戳）
2. 初始化 `TradingLogger` → `TradingMonitor` → `ReportScheduler`
3. 初始化 `DingTalkBot` → `TradingAlert`，发送启动通知
4. 创建 `XtQuantTrader` 实例，`connect()` 连接 MiniQMT
5. 订阅账户 `StockAccount`，注册 `LoggingCallback`
6. 创建 `TradingEngine`，添加 `MyStrategy` 策略，启动引擎
   - `MyStrategy(engine.signal_queue, trader, acc, logger, alert)` — 五参数构造
7. 创建 `TradingScheduler`，启动时间调度
8. 创建 `HealthChecker`，启动健康检查
9. 进入 `while True` 主循环，每分钟刷新 `last_activity`

**异常处理**:
- 连接失败 (`connect() != 0`): 记录错误日志、发送告警、抛出异常
- `KeyboardInterrupt`: 优雅退出，逐一停止所有组件
- `RobustTrader` 外层捕获: 崩溃后最多重试 10 次（间隔 60 秒）

## 入口

```python
if __name__ == '__main__':
    robust_trader = RobustTrader(main, max_retries=10, retry_interval=60)
    robust_trader.run()
```

`RobustTrader` 提供崩溃自动重启机制，详见 [robust.md](robust.md)。

## 依赖

- `xtquant`: MiniQMT SDK（`XtQuantTrader`, `StockAccount`）
- `qlib_trader.*`: 内部模块（trading_engine, strategy, alert, logger, scheduler, health_checker, robust）
- `yaml`: 配置解析
- `pathlib`: 路径处理

## 注意事项

1. 所有组件必须按顺序初始化，顺序错误可能导致依赖缺失
2. `CONFIG` 为模块级变量，在 `import` 时即加载，请确保配置文件存在
3. `model_path` 配置项仅供 `generate_pred_score.py` 使用，`main.py` 本身不读取模型
4. 调试时可将 `RobustTrader` 注释，直接调用 `main()` 方便查看错误
