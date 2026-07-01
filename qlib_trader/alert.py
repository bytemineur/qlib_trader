import requests
import json
import time
import hmac
import hashlib
import base64
import urllib.parse
from datetime import datetime


class DingTalkBot:
    """钉钉机器人"""
    
    def __init__(self, webhook, secret=None):
        self.webhook = webhook
        self.secret = secret
    
    def _get_sign(self):
        """计算加签"""
        if not self.secret:
            return None, None
        timestamp = str(round(time.time() *1000))
        secret_enc = self.secret.encode('utf-8')
        string_to_sign = f'{timestamp}\n{self.secret}'
        hmac_code = hmac.new(
            secret_enc, string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha256,
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return timestamp, sign
    
    def _get_url(self):
        if self.secret:
            ts, sign = self._get_sign()
            return f"{self.webhook}&timestamp={ts}&sign={sign}"
        return self.webhook
    
    def _send(self, data):
        try:
            resp = requests.post(
                self._get_url(),
                headers={'Content-Type': 'application/json'},
                data=json.dumps(data),
                timeout=5,
            )
            result = resp.json()
            if result.get('errcode') != 0:
                print(f"钉钉发送失败: {result}")
                return False
            return True
        except Exception as e:
            print(f"钉钉发送异常: {e}")
            return False
    
    def send_text(self, content, at_mobiles=None, at_all=False):
        """文本消息（支持@人）"""
        data = {
            "msgtype": "text",
            "text": {"content": content},
            "at": {
                "atMobiles": at_mobiles or [],
                "isAtAll": at_all,
            },
        }
        return self._send(data)
    
    def send_markdown(self, title, text, at_mobiles=None):
        """Markdown 消息（支持加粗、链接等）"""
        data = {
            "msgtype": "markdown",
            "markdown": {"title": title, "text": text},
            "at": {
                "atMobiles": at_mobiles or [],
                "isAtAll": False,
            },
        }
        return self._send(data)
    
class TradingAlert:
    """交易告警（封装常见场景）"""
    
    def __init__(self, bot):
        self.bot = bot
        self.enabled = True
    
    def alert_signal(self, strategy, stock_code, signal_type, reason):
        """信号告警"""
        if not self.enabled:
            return
        emoji = "📈" if signal_type == "buy" else "📉"
        content = (
            f"{emoji} 【{strategy}信号】\n"
            f"股票: {stock_code}\n"
            f"方向: {signal_type.upper()}\n"
            f"原因: {reason}"
        )
        self.bot.send_text(content)
    
    def alert_trade(self, stock_code, direction, volume, price, amount):
        """成交告警"""
        if not self.enabled:
            return
        emoji = "🟢" if direction == "买入" else "🔴"
        content = (
            f"{emoji} 【成交通知】\n"
            f"股票: {stock_code}\n"
            f"方向: {direction}\n"
            f"数量: {volume}股\n"
            f"价格: {price}\n"
            f"金额: {amount:,.2f}元"
        )
        self.bot.send_text(content)
    
    def alert_error(self, error_type, message):
        """错误告警"""
        content = (
            f"🚨 【系统告警】\n"
            f"类型: {error_type}\n"
            f"信息: {message}"
        )
        self.bot.send_text(content)
    
    def alert_daily_report(self, report):
        """每日汇总"""
        title = f"📊 交易日报 - {datetime.now().strftime('%Y-%m-%d')}"
        if hasattr(self.bot, 'send_markdown'):
            self.bot.send_markdown(title, report)
        elif hasattr(self.bot, 'send_card'):
            self.bot.send_card(title, report, "blue")
        else:
            self.bot.send_text(f"{title}\n{report}")
