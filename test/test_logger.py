"""
test_logger.py — 日志与监控模块测试用例
"""
import sys
from unittest.mock import MagicMock

# Mock 缺失模块
sys.modules['schedule'] = MagicMock()
sys.modules['xtquant'] = MagicMock()
sys.modules['xtquant.xttrader'] = MagicMock()
sys.modules['xtquant.xttype'] = MagicMock()
sys.modules['xtquant.xtconstant'] = MagicMock()

import unittest
import os
import tempfile
import logging
from unittest.mock import Mock, MagicMock as MM

sys.path.insert(0, "/mnt/c/Users/zhh/Desktop/qlib_trader/qlib_trader")



class TestSetupLogger(unittest.TestCase):
    """setup_logger 函数测试"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_creates_log_dir(self):
        """自动创建日志目录"""
        log_dir = os.path.join(self.tmpdir, "new_logs")
        from logger import setup_logger
        logger = setup_logger("test", log_dir)
        self.assertTrue(os.path.isdir(log_dir))
        self.assertIsInstance(logger, logging.Logger)

    def test_returns_logger_with_handlers(self):
        """返回的 logger 包含 file 和 console handler"""
        from logger import setup_logger
        logger = setup_logger("test_uniq_" + str(id(self)), self.tmpdir)
        self.assertEqual(len(logger.handlers), 2)


class TestTradingLogger(unittest.TestCase):
    """TradingLogger 测试"""

    def setUp(self):
        from logger import TradingLogger
        self.tmpdir = tempfile.mkdtemp()
        self.tl = TradingLogger(log_dir=self.tmpdir)

    def test_has_three_loggers(self):
        """有三个独立的 logger"""
        self.assertIsNotNone(self.tl.logger)
        self.assertIsNotNone(self.tl.order_logger)
        self.assertIsNotNone(self.tl.signal_logger)

    def test_log_signal(self):
        """信号日志写入"""
        self.tl.log_signal("Strat", "000001.SZ", "buy", "reason")
        # 验证 signals.log 被创建
        files = os.listdir(self.tmpdir)
        self.assertTrue(any("signals" in f for f in files))

    def test_log_order(self):
        """委托日志写入"""
        self.tl.log_order("ORD123", "000001.SZ", "买入", 100, 10.5, "已报")
        files = os.listdir(self.tmpdir)
        self.assertTrue(any("orders" in f for f in files))

    def test_log_trade(self):
        """成交日志写入"""
        self.tl.log_trade("ORD123", "000001.SZ", 100, 10.5, 1050)
        files = os.listdir(self.tmpdir)
        self.assertTrue(any("orders" in f for f in files))

    def test_log_error_with_detail(self):
        """错误日志（含详情）"""
        self.tl.log_error("NET", "timeout", detail="3 retries")
        files = os.listdir(self.tmpdir)
        self.assertTrue(any("trading" in f for f in files))

    def test_log_error_without_detail(self):
        """错误日志（无详情）"""
        self.tl.log_error("NET", "timeout")
        # 不应抛异常


class TestTradingMonitor(unittest.TestCase):
    """TradingMonitor 测试"""

    def setUp(self):
        from logger import TradingMonitor
        self.monitor = TradingMonitor()

    def test_initial_metrics_zero(self):
        """初始指标全为0"""
        self.assertEqual(self.monitor.metrics["signals_total"], 0)
        self.assertEqual(self.monitor.metrics["orders_total"], 0)
        self.assertEqual(self.monitor.metrics["trades_total"], 0)

    def test_on_signal(self):
        """信号计数"""
        self.monitor.on_signal("000001.SZ")
        self.monitor.on_signal("000001.SZ")
        self.assertEqual(self.monitor.metrics["signals_total"], 2)

    def test_on_order_success(self):
        """成功委托"""
        self.monitor.on_order("000001.SZ", success=True)
        self.assertEqual(self.monitor.metrics["orders_success"], 1)
        self.assertEqual(self.monitor.metrics["orders_failed"], 0)

    def test_on_order_failed(self):
        """失败委托"""
        self.monitor.on_order("000001.SZ", success=False)
        self.assertEqual(self.monitor.metrics["orders_failed"], 1)
        self.assertEqual(self.monitor.metrics["orders_success"], 0)

    def test_on_trade(self):
        """成交统计"""
        self.monitor.on_trade("000001.SZ", 1000)
        self.monitor.on_trade("600519.SH", 2000)
        self.assertEqual(self.monitor.metrics["trades_total"], 2)
        self.assertEqual(self.monitor.metrics["trades_amount"], 3000)
        self.assertEqual(self.monitor.stock_metrics["000001.SZ"]["amount"], 1000)

    def test_on_error(self):
        """错误计数"""
        self.monitor.on_error()
        self.monitor.on_error()
        self.assertEqual(self.monitor.metrics["errors_total"], 2)

    def test_get_report_contains_keys(self):
        """报告包含关键信息"""
        self.monitor.on_signal("000001.SZ")
        self.monitor.on_order("000001.SZ", success=True)
        self.monitor.on_trade("000001.SZ", 5000)
        report = self.monitor.get_report()
        self.assertIn("信号总数", report)
        self.assertIn("成功委托", report)
        self.assertIn("成交金额", report)

    def test_get_report_no_division_by_zero(self):
        """成功率不除零：0/1=0.0%"""
        report = self.monitor.get_report()
        # 公式：orders_success / max(1, orders_total) * 100
        # 初始均为0 → 0 / 1 * 100 = 0.0%
        self.assertIn("0.0%", report)

    def test_stock_metrics_aggregation(self):
        """分股票聚合"""
        self.monitor.on_trade("A.SZ", 100)
        self.monitor.on_trade("A.SZ", 200)
        self.monitor.on_trade("B.SH", 300)
        self.assertEqual(self.monitor.stock_metrics["A.SZ"]["trades"], 2)
        self.assertEqual(self.monitor.stock_metrics["A.SZ"]["amount"], 300)
        self.assertEqual(self.monitor.stock_metrics["B.SH"]["trades"], 1)


if __name__ == "__main__":
    unittest.main()
