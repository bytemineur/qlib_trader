"""
test_health_checker.py — 健康检查模块测试用例
"""
import sys
from unittest.mock import MagicMock

# Mock psutil（如未安装）
try:
    import psutil
except ImportError:
    sys.modules['psutil'] = MagicMock()

import unittest
from unittest.mock import Mock, patch, PropertyMock
import time

sys.path.insert(0, "/mnt/c/Users/zhh/Desktop/qlib_trader/qlib_trader")



class MockTradingSystem:
    """模拟交易系统"""
    def __init__(self):
        self.trader = Mock()
        self.acc = Mock()
        self.last_activity = time.time()


class TestHealthChecker(unittest.TestCase):
    """HealthChecker 测试"""

    def setUp(self):
        from health_checker import HealthChecker
        self.trading_sys = MockTradingSystem()
        self.alert_calls = []
        self.checker = HealthChecker(
            self.trading_sys,
            alert_func=lambda et, msg: self.alert_calls.append((et, msg))
        )

    def tearDown(self):
        self.checker.stop()

    def test_init_defaults(self):
        """默认属性值"""
        self.assertFalse(self.checker.running)
        self.assertEqual(self.checker.check_interval, 60)

    def test_start_stop(self):
        """启动和停止"""
        self.checker.start()
        self.assertTrue(self.checker.running)
        self.checker.stop()
        self.assertFalse(self.checker.running)

    def test_check_connection_success(self):
        """连接正常"""
        self.trading_sys.trader.query_stock_asset.return_value = {"asset": 100000}
        result = self.checker._check_connection()
        self.assertTrue(result)

    def test_check_connection_failure(self):
        """连接失败"""
        self.trading_sys.trader.query_stock_asset.side_effect = Exception("disconnected")
        result = self.checker._check_connection()
        self.assertFalse(result)

    def test_check_heartbeat_ok(self):
        """心跳正常"""
        self.trading_sys.last_activity = time.time()
        result = self.checker._check_heartbeat()
        self.assertTrue(result)

    def test_check_heartbeat_timeout(self):
        """心跳超时"""
        self.trading_sys.last_activity = time.time() - 400  # 超过5分钟
        result = self.checker._check_heartbeat()
        self.assertFalse(result)

    def test_check_memory_ok(self):
        """内存正常"""
        import sys as _sys
        from unittest.mock import MagicMock
        _old = _sys.modules.get("psutil")
        mock_psutil = MagicMock()
        mock_process = MagicMock()
        mock_process.memory_info.return_value.rss = 100 * 1024 * 1024
        mock_psutil.Process.return_value = mock_process
        _sys.modules["psutil"] = mock_psutil
        try:
            result = self.checker._check_memory()
        finally:
            if _old is not None:
                _sys.modules["psutil"] = _old
            else:
                _sys.modules.pop("psutil", None)
        self.assertTrue(result)

    def test_check_memory_high(self):
        """内存过高"""
        import sys as _sys
        from unittest.mock import MagicMock
        _old = _sys.modules.get("psutil")
        mock_psutil = MagicMock()
        mock_process = MagicMock()
        mock_process.memory_info.return_value.rss = 600 * 1024 * 1024
        mock_psutil.Process.return_value = mock_process
        _sys.modules["psutil"] = mock_psutil
        try:
            result = self.checker._check_memory()
        finally:
            if _old is not None:
                _sys.modules["psutil"] = _old
            else:
                _sys.modules.pop("psutil", None)
        self.assertFalse(result)

    def test_do_check_all_ok(self):
        """全部检查通过时不触发告警"""
        import sys as _sys
        from unittest.mock import MagicMock
        self.trading_sys.trader.query_stock_asset.return_value = {"asset": 100000}
        self.trading_sys.last_activity = time.time()

        # mock psutil in sys.modules
        _old = _sys.modules.get("psutil")
        mock_psutil = MagicMock()
        mock_process = MagicMock()
        mock_process.memory_info.return_value.rss = 100 * 1024 * 1024
        mock_psutil.Process.return_value = mock_process
        _sys.modules["psutil"] = mock_psutil
        try:
            self.checker._do_check()
        finally:
            if _old is not None:
                _sys.modules["psutil"] = _old
            else:
                _sys.modules.pop("psutil", None)

        self.assertEqual(len(self.alert_calls), 0)

    def test_do_check_with_issues(self):
        """有问题时触发告警"""
        import sys as _sys
        from unittest.mock import MagicMock
        self.trading_sys.trader.query_stock_asset.side_effect = Exception("down")
        self.trading_sys.last_activity = 0  # 心跳超时

        _old = _sys.modules.get("psutil")
        mock_psutil = MagicMock()
        mock_process = MagicMock()
        mock_process.memory_info.return_value.rss = 100 * 1024 * 1024
        mock_psutil.Process.return_value = mock_process
        _sys.modules["psutil"] = mock_psutil
        try:
            self.checker._do_check()
        finally:
            if _old is not None:
                _sys.modules["psutil"] = _old
            else:
                _sys.modules.pop("psutil", None)

        self.assertGreater(len(self.alert_calls), 0)


if __name__ == "__main__":
    unittest.main()
