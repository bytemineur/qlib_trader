"""
test_robust.py — 健壮性保障模块测试用例
"""
import unittest
from unittest.mock import Mock, patch
import sys
import io

sys.path.insert(0, "/mnt/c/Users/zhh/Desktop/qlib_trader/qlib_trader")


class TestRobustTrader(unittest.TestCase):
    """RobustTrader 测试"""

    def setUp(self):
        from robust import RobustTrader
        self.call_count = 0

    def _make_trader(self, fail_times=0, interrupt=False):
        """构造测试用的 trader_func"""
        def func():
            self.call_count += 1
            if interrupt:
                raise KeyboardInterrupt()
            if self.call_count <= fail_times:
                raise RuntimeError(f"fail #{self.call_count}")
            # 成功
        return func

    def test_normal_execution(self):
        """正常执行一次"""
        from robust import RobustTrader
        trader_func = self._make_trader(fail_times=0)
        rt = RobustTrader(trader_func, max_retries=3, retry_interval=0.01)
        rt.run()
        self.assertEqual(self.call_count, 1)
        self.assertEqual(rt.retry_count, 0)

    def test_retry_on_failure(self):
        """失败后重试"""
        from robust import RobustTrader
        trader_func = self._make_trader(fail_times=2)  # 失败2次后成功
        rt = RobustTrader(trader_func, max_retries=5, retry_interval=0.01)
        rt.run()
        self.assertEqual(self.call_count, 3)  # 第3次成功
        self.assertEqual(rt.retry_count, 2)

    @patch("sys.exit")
    def test_max_retries_exceeded(self, mock_exit):
        """超过最大重试次数"""
        from robust import RobustTrader
        trader_func = self._make_trader(fail_times=999)  # 永远失败
        rt = RobustTrader(trader_func, max_retries=2, retry_interval=0.01)
        rt.run()
        self.assertEqual(rt.retry_count, 2)
        mock_exit.assert_called_once_with(1)

    def test_keyboard_interrupt_passthrough(self):
        """KeyboardInterrupt 直接穿透"""
        from robust import RobustTrader
        trader_func = self._make_trader(interrupt=True)
        rt = RobustTrader(trader_func, max_retries=5, retry_interval=0.01)

        with self.assertRaises(KeyboardInterrupt):
            rt.run()

        self.assertEqual(self.call_count, 1)
        self.assertEqual(rt.retry_count, 0)

    def test_retry_interval_respected(self):
        """重试间隔被遵守"""
        from robust import RobustTrader
        import time

        trader_func = self._make_trader(fail_times=1)
        rt = RobustTrader(trader_func, max_retries=3, retry_interval=0.2)

        start = time.time()
        rt.run()
        elapsed = time.time() - start

        self.assertGreaterEqual(elapsed, 0.2)
        self.assertEqual(self.call_count, 2)


if __name__ == "__main__":
    unittest.main()
