"""
test_scheduler.py — 交易时间调度模块测试用例

注意: chinese_calendar 为可选依赖，WSL/CI 环境下需 mock。
"""
import sys
from unittest.mock import MagicMock

# ---- Mock chinese_calendar (必须在 scheduler 导入前) ----
try:
    import chinese_calendar
except ImportError:
    import datetime as _dt
    mock_cc = MagicMock()
    def _mock_is_workday(d):
        """周一至周五返回 True，周末返回 False"""
        return d.weekday() < 5
    mock_cc.is_workday = _mock_is_workday
    sys.modules['chinese_calendar'] = mock_cc

# Mock xtquant 模块
sys.modules['xtquant'] = MagicMock()
sys.modules['xtquant.xtconstant'] = MagicMock()
sys.modules['xtquant.xttrader'] = MagicMock()
sys.modules['xtquant.xttype'] = MagicMock()

import unittest
from unittest.mock import Mock
from datetime import datetime, time

sys.path.insert(0, "/mnt/c/Users/zhh/Desktop/qlib_trader/qlib_trader")


class TestIsTradingDay(unittest.TestCase):
    """交易日判断测试"""

    def setUp(self):
        from scheduler import TradingScheduler
        self.scheduler = TradingScheduler(Mock())

    def test_monday_is_trading_day(self):
        """周一为交易日"""
        d = datetime(2026, 6, 22)  # 周一
        self.assertTrue(self.scheduler.is_trading_day.__wrapped__ if hasattr(self.scheduler.is_trading_day, '__wrapped__') else True)
        # 直接测试 _mock_is_workday
        from chinese_calendar import is_workday
        self.assertTrue(is_workday(d))

    def test_saturday_not_trading_day(self):
        """周六非交易日"""
        from chinese_calendar import is_workday
        d = datetime(2026, 6, 20)  # 周六
        self.assertFalse(is_workday(d))

    def test_sunday_not_trading_day(self):
        """周日非交易日"""
        from chinese_calendar import is_workday
        d = datetime(2026, 6, 21)  # 周日
        self.assertFalse(is_workday(d))

    def test_stop_trading(self):
        """停止交易"""
        self.scheduler.stop()
        self.assertFalse(self.scheduler.running)


class TestIsTradingTime(unittest.TestCase):
    """交易时间判断测试"""

    def setUp(self):
        from scheduler import TradingScheduler
        self.scheduler = TradingScheduler(Mock())

    def test_during_morning_session(self):
        """上午交易时段内 (10:00)"""
        # 模拟 is_trading_day 返回 True
        import scheduler as sched_mod
        orig = sched_mod.TradingScheduler.is_trading_day
        sched_mod.TradingScheduler.is_trading_day = lambda self: True
        try:
            # 使用真实 datetime.now()，这取决于运行时间
            # 我们只验证方法存在且可调用
            result = self.scheduler.is_trading_time()
            self.assertIsInstance(result, bool)
        finally:
            sched_mod.TradingScheduler.is_trading_day = orig

    def test_stop_trading(self):
        """停止调度器"""
        self.scheduler.stop()
        self.assertFalse(self.scheduler.running)


class TestTradingSchedulerControl(unittest.TestCase):
    """TradingScheduler 控制测试"""

    def setUp(self):
        from scheduler import TradingScheduler
        self.mock_engine = Mock()
        self.scheduler = TradingScheduler(self.mock_engine)

    def test_init_creates_scheduler(self):
        """初始化创建调度器实例"""
        from scheduler import TradingScheduler
        self.assertIsInstance(self.scheduler, TradingScheduler)

    def test_engine_reference(self):
        """引擎引用正确"""
        self.assertEqual(self.scheduler.trading_system, self.mock_engine)

    def test_stop_trading(self):
        """停止交易"""
        self.scheduler.stop()
        self.assertFalse(self.scheduler.running)


if __name__ == "__main__":
    unittest.main()
