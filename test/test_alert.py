"""
test_alert.py — 告警模块测试用例
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import json


# ---------------------------------------------------------------------------
# 导入被测模块（mock 掉外部依赖）
# ---------------------------------------------------------------------------
import sys
sys.path.insert(0, "/mnt/c/Users/zhh/Desktop/qlib_trader/qlib_trader")

# Mock requests 防止真实网络调用
import importlib
import requests as real_requests


class TestDingTalkBot(unittest.TestCase):
    """DingTalkBot 单元测试"""

    def setUp(self):
        self.webhook = "https://oapi.dingtalk.com/robot/send?access_token=test"
        self.secret = "SECtest"

    # ---- 构造 ----
    def test_init_without_secret(self):
        """无 secret 构造"""
        from alert import DingTalkBot
        bot = DingTalkBot(self.webhook)
        self.assertEqual(bot.webhook, self.webhook)
        self.assertIsNone(bot.secret)

    def test_init_with_secret(self):
        """带 secret 构造"""
        from alert import DingTalkBot
        bot = DingTalkBot(self.webhook, secret=self.secret)
        self.assertEqual(bot.secret, self.secret)

    # ---- 加签 ----
    def test_get_sign_without_secret(self):
        """无 secret 时 _get_sign 返回 (None, None)"""
        from alert import DingTalkBot
        bot = DingTalkBot(self.webhook)
        ts, sign = bot._get_sign()
        self.assertIsNone(ts)
        self.assertIsNone(sign)

    def test_get_sign_with_secret(self):
        """有 secret 时 _get_sign 返回有效的 timestamp 和 sign"""
        from alert import DingTalkBot
        bot = DingTalkBot(self.webhook, secret=self.secret)
        ts, sign = bot._get_sign()
        self.assertIsNotNone(ts)
        self.assertIsNotNone(sign)
        self.assertTrue(ts.isdigit())
        self.assertTrue(len(sign) > 0)

    # ---- URL 拼接 ----
    def test_get_url_without_secret(self):
        """无 secret 时返回原始 webhook"""
        from alert import DingTalkBot
        bot = DingTalkBot(self.webhook)
        self.assertEqual(bot._get_url(), self.webhook)

    def test_get_url_with_secret(self):
        """有 secret 时 URL 包含 timestamp 和 sign"""
        from alert import DingTalkBot
        bot = DingTalkBot(self.webhook, secret=self.secret)
        url = bot._get_url()
        self.assertIn("timestamp=", url)
        self.assertIn("sign=", url)

    # ---- 发送 ----
    @patch("alert.requests.post")
    def test_send_text_success(self, mock_post):
        """send_text 成功"""
        from alert import DingTalkBot
        mock_resp = Mock()
        mock_resp.json.return_value = {"errcode": 0}
        mock_post.return_value = mock_resp

        bot = DingTalkBot(self.webhook)
        result = bot.send_text("hello")
        self.assertTrue(result)

    @patch("alert.requests.post")
    def test_send_text_failure_errcode(self, mock_post):
        """send_text 失败（errcode 非0）"""
        from alert import DingTalkBot
        mock_resp = Mock()
        mock_resp.json.return_value = {"errcode": 1, "errmsg": "error"}
        mock_post.return_value = mock_resp

        bot = DingTalkBot(self.webhook)
        result = bot.send_text("hello")
        self.assertFalse(result)

    @patch("alert.requests.post")
    def test_send_text_exception(self, mock_post):
        """send_text 网络异常"""
        from alert import DingTalkBot
        mock_post.side_effect = Exception("network error")

        bot = DingTalkBot(self.webhook)
        result = bot.send_text("hello")
        self.assertFalse(result)

    # ---- Markdown ----
    @patch("alert.requests.post")
    def test_send_markdown(self, mock_post):
        """send_markdown 消息格式正确"""
        from alert import DingTalkBot
        mock_resp = Mock()
        mock_resp.json.return_value = {"errcode": 0}
        mock_post.return_value = mock_resp

        bot = DingTalkBot(self.webhook)
        bot.send_markdown("title", "## body")

        call_data = json.loads(mock_post.call_args[1]["data"])
        self.assertEqual(call_data["msgtype"], "markdown")
        self.assertEqual(call_data["markdown"]["title"], "title")
        self.assertEqual(call_data["markdown"]["text"], "## body")

    # ---- @人 ----
    @patch("alert.requests.post")
    def test_at_mobiles(self, mock_post):
        """send_text 包含 @ 列表"""
        from alert import DingTalkBot
        mock_resp = Mock()
        mock_resp.json.return_value = {"errcode": 0}
        mock_post.return_value = mock_resp

        bot = DingTalkBot(self.webhook)
        bot.send_text("hello", at_mobiles=["13800138000"], at_all=False)

        call_data = json.loads(mock_post.call_args[1]["data"])
        self.assertEqual(call_data["at"]["atMobiles"], ["13800138000"])
        self.assertFalse(call_data["at"]["isAtAll"])

    @patch("alert.requests.post")
    def test_at_all(self, mock_post):
        """send_text @所有人"""
        from alert import DingTalkBot
        mock_resp = Mock()
        mock_resp.json.return_value = {"errcode": 0}
        mock_post.return_value = mock_resp

        bot = DingTalkBot(self.webhook)
        bot.send_text("hello", at_all=True)

        call_data = json.loads(mock_post.call_args[1]["data"])
        self.assertTrue(call_data["at"]["isAtAll"])


class TestTradingAlert(unittest.TestCase):
    """TradingAlert 单元测试"""

    def setUp(self):
        from alert import TradingAlert
        self.mock_bot = MagicMock()
        self.alert = TradingAlert(self.mock_bot)

    def test_enabled_default_true(self):
        """默认 enabled=True"""
        self.assertTrue(self.alert.enabled)

    def test_disabled_skips_alert(self):
        """enabled=False 时不发送告警"""
        self.alert.enabled = False
        self.alert.alert_signal("s", "000001.SZ", "buy", "reason")
        self.mock_bot.send_text.assert_not_called()

    def test_alert_signal_buy(self):
        """买入信号告警"""
        self.alert.alert_signal("TestStrat", "000001.SZ", "buy", "金叉")
        self.mock_bot.send_text.assert_called_once()
        call_content = self.mock_bot.send_text.call_args[0][0]
        self.assertIn("TestStrat", call_content)
        self.assertIn("000001.SZ", call_content)
        self.assertIn("BUY", call_content)
        self.assertIn("金叉", call_content)

    def test_alert_signal_sell(self):
        """卖出信号告警"""
        self.alert.alert_signal("TestStrat", "600519.SH", "sell", "死叉")
        call_content = self.mock_bot.send_text.call_args[0][0]
        self.assertIn("SELL", call_content)

    def test_alert_trade(self):
        """成交通知"""
        self.alert.alert_trade("000001.SZ", "买入", 100, 10.5, 1050.0)
        call_content = self.mock_bot.send_text.call_args[0][0]
        self.assertIn("买入", call_content)
        self.assertIn("100股", call_content)
        self.assertIn("1,050.00", call_content)

    def test_alert_error(self):
        """错误告警"""
        self.alert.alert_error("NETWORK", "超时")
        call_content = self.mock_bot.send_text.call_args[0][0]
        self.assertIn("NETWORK", call_content)
        self.assertIn("超时", call_content)

    def test_alert_daily_report_with_markdown(self):
        """日报优先使用 markdown"""
        self.alert.alert_daily_report("## 日报")
        self.mock_bot.send_markdown.assert_called_once()

    def test_alert_daily_report_fallback_text(self):
        """日报降级为 text（无 send_markdown/send_card）"""
        from unittest.mock import Mock
        # 创建一个只有 send_text 属性的 bot（用 spec 限制）
        from alert import TradingAlert

        # 直接用 MagicMock 并删除不需要的属性
        from unittest.mock import MagicMock
        text_only_bot = MagicMock()
        # 删除 send_markdown 和 send_card 使得降级生效
        del text_only_bot.send_markdown
        del text_only_bot.send_card

        alert = TradingAlert(text_only_bot)
        alert.alert_daily_report("report")
        text_only_bot.send_text.assert_called_once()


if __name__ == "__main__":
    unittest.main()
