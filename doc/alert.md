# alert.py — 告警模块

## 概述

告警模块封装了钉钉机器人的消息推送能力和交易场景下的常用告警模板，是整个无人值守交易系统的"耳目"。当系统产生交易信号、成交回报、异常错误或需要发送每日汇总时，通过该模块向钉钉群推送通知。

## 类说明

### `DingTalkBot`

钉钉机器人客户端，负责与钉钉 Webhook 通信。

**构造参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `webhook` | `str` | 钉钉机器人 Webhook 地址 |
| `secret` | `str` (可选) | 加签密钥，用于安全校验。传入后启用加签模式 |

**方法**

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `send_text(content, at_mobiles, at_all)` | `content`: 消息文本; `at_mobiles`: @的手机号列表; `at_all`: 是否@所有人 | `bool` | 发送纯文本消息 |
| `send_markdown(title, text, at_mobiles)` | `title`: 标题; `text`: Markdown 正文; `at_mobiles`: @列表 | `bool` | 发送 Markdown 格式消息 |

**内部方法**

| 方法 | 说明 |
|------|------|
| `_get_sign()` | 生成加签时间戳和签名，返回 `(timestamp, sign)` 元组 |
| `_get_url()` | 拼接带签名参数的完整 Webhook URL |
| `_send(data)` | 通用发送逻辑，POST JSON 到 Webhook |

**使用示例**

```python
bot = DingTalkBot(webhook_url, secret="SEC...")
bot.send_text("交易系统启动")
bot.send_markdown("日报", "### 今日交易汇总\n- 成交: 10笔")
```

---

### `TradingAlert`

交易告警封装，将常见告警场景（信号、成交、错误、日报）模板化，统一通过一个 `DingTalkBot` 实例发送。

**构造参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| `bot` | `DingTalkBot` | 已初始化的钉钉机器人实例 |

**属性**

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enabled` | `bool` | `True` | 告警开关，设为 `False` 可静默所有告警 |

**方法**

| 方法 | 参数 | 说明 |
|------|------|------|
| `alert_signal(strategy, stock_code, signal_type, reason)` | `strategy`: 策略名; `stock_code`: 股票代码; `signal_type`: `"buy"`/`"sell"`; `reason`: 信号原因 | 发送交易信号告警，包含方向emoji |
| `alert_trade(stock_code, direction, volume, price, amount)` | `stock_code`: 股票代码; `direction`: `"买入"`/`"卖出"`; `volume`: 成交数量(股); `price`: 成交价; `amount`: 成交金额 | 发送成交通知，包含金额格式化 |
| `alert_error(error_type, message)` | `error_type`: 错误类型; `message`: 错误信息 | 发送系统错误告警 |
| `alert_daily_report(report)` | `report`: 日报内容（文本/Markdown） | 发送每日汇总，优先使用 Markdown 格式 |

**使用示例**

```python
alert = TradingAlert(bot)
alert.alert_signal("双均线策略", "000001.SZ", "buy", "金叉突破")
alert.alert_trade("000001.SZ", "买入", 100, 10.5, 1050.0)
alert.alert_error("NETWORK", "QMT连接超时")
alert.alert_daily_report("今日成交10笔，盈亏+500元")
```

## 依赖

- `requests`: HTTP POST 请求
- `hmac`, `hashlib`, `base64`, `urllib.parse`: 加签计算
- `datetime`: 日报时间戳

## 注意事项

1. `DingTalkBot._send()` 内置 `try/except`，发送失败不会抛异常，而是打印错误并返回 `False`
2. 加签模式下，时间戳取客户端本地毫秒时间
3. `TradingAlert.alert_daily_report()` 会检测 `bot` 是否支持 `send_markdown` 或 `send_card`，按优先级降级发送
