"""
test_strategy.py — 策略模块测试用例

注意: pandas/xtquant 为 Windows 环境依赖，WSL/CI 环境下需 mock。
"""
import sys
from unittest.mock import MagicMock

# Mock xtquant 模块（Windows 专有，WSL 不可用）
sys.modules['xtquant'] = MagicMock()
sys.modules['xtquant.xtconstant'] = MagicMock()
sys.modules['xtquant.xttrader'] = MagicMock()
sys.modules['xtquant.xttype'] = MagicMock()
sys.modules['xtquant.xtdata'] = MagicMock()

# Mock pandas（如果未安装）
try:
    import pandas
except ImportError:
    sys.modules['pandas'] = MagicMock()

import xtquant.xtconstant as xtc
xtc.STOCK_BUY = 23
xtc.STOCK_SELL = 24
xtc.FIX_PRICE = 11

import unittest
import time
import datetime
from unittest.mock import Mock, MagicMock as MM, patch, PropertyMock

sys.path.insert(0, "/mnt/c/Users/zhh/Desktop/qlib_trader/qlib_trader")


class TestMyStrategy(unittest.TestCase):
    """MyStrategy 策略测试 — 五参数构造函数（queue, xt_trader, acc, logger, alert）"""

    def setUp(self):
        from trading_engine import SignalQueue
        from strategy import MyStrategy

        self.queue = SignalQueue()
        self.mock_trader = MM()
        self.mock_acc = MM()
        self.mock_logger = MM()
        self.mock_alert = MM()

        self.strategy = MyStrategy(
            queue=self.queue,
            xt_trader=self.mock_trader,
            acc=self.mock_acc,
            logger=self.mock_logger,
            alert=self.mock_alert
        )

    def test_strategy_name(self):
        """策略名称包含 TopkDropout 和 沪深300指数增强"""
        self.assertIn("TopkDropout", self.strategy.strategy_name)
        self.assertIn("沪深300", self.strategy.strategy_name)

    def test_topk_default(self):
        """默认 topk=50"""
        self.assertEqual(self.strategy.topk, 50)

    def test_n_drop_default(self):
        """默认 n_drop=5"""
        self.assertEqual(self.strategy.n_drop, 5)

    def test_cash_default(self):
        """默认 cash=20000"""
        self.assertEqual(self.strategy.cash, 20_000)

    def test_last_rebalance_date_initial_none(self):
        """初始 last_rebalance_date 为 None"""
        self.assertIsNone(self.strategy.last_rebalance_date)

    def test_inherits_signal_producer(self):
        """继承自 SignalProducer"""
        from trading_engine import SignalProducer
        self.assertIsInstance(self.strategy, SignalProducer)

    def test_constructor_injects_dependencies(self):
        """构造函数正确注入依赖"""
        self.assertEqual(self.strategy.xt_trader, self.mock_trader)
        self.assertEqual(self.strategy.acc, self.mock_acc)
        self.assertEqual(self.strategy.logger, self.mock_logger)
        self.assertEqual(self.strategy.alert, self.mock_alert)

    def test_start_stop(self):
        """启动和停止"""
        self.strategy.start()
        self.assertTrue(self.strategy.running)
        time.sleep(0.1)
        self.strategy.stop()
        self.assertFalse(self.strategy.running)

    def test_generate_signals_empty_by_default(self):
        """非14:50 不产生信号"""
        self.strategy._generate_signals()
        self.assertTrue(self.queue.empty())

    def test_run_calls_generate_signals(self):
        """_run 循环会调用 _generate_signals"""
        original_gen = self.strategy._generate_signals
        call_count = [0]
        def counting_gen():
            call_count[0] += 1
        self.strategy._generate_signals = counting_gen
        self.strategy.start()
        time.sleep(0.3)
        self.strategy.stop()
        self.strategy._generate_signals = original_gen
        self.assertGreaterEqual(call_count[0], 1)


class TestGetDropoutTradeList(unittest.TestCase):
    """_get_dropout_trade_list 算法测试"""

    def setUp(self):
        # 使用纯 Python 数据结构，不依赖 pandas
        self.pred_score = {
            'A': 0.9, 'B': 0.8, 'C': 0.7, 'D': 0.6, 'E': 0.5
        }

    def _call(self, holdings, topk=3, n_drop=1):
        from strategy import MyStrategy
        # 转换为类似 pandas Series 的对象
        class FakeSeries:
            def __init__(self, data):
                self._data = data
                self.index = list(data.keys())
            def dropna(self):
                return FakeSeries({k: v for k, v in self._data.items() if v is not None})
            def get(self, key, default):
                return self._data.get(key, default)
            def min(self):
                return min(self._data.values()) if self._data else 0
            def sort_values(self, ascending=True, **kwargs):
                sorted_items = sorted(self._data.items(), key=lambda x: x[1], reverse=not ascending)
                return FakeSeries(dict(sorted_items))
            def head(self, n):
                items = list(self._data.items())[:n]
                return FakeSeries(dict(items))
            def __getitem__(self, key):
                return self._data[key]
            def __contains__(self, key):
                return key in self._data
            def __iter__(self):
                return iter(self._data)
            def __len__(self):
                return len(self._data)

        ps = FakeSeries(self.pred_score)
        return MyStrategy._get_dropout_trade_list(ps, holdings, topk, n_drop)

    def test_empty_holdings(self):
        """空持仓：买入 topk 只"""
        buy, sell = self._call([], topk=3, n_drop=1)
        self.assertEqual(len(sell), 0)
        self.assertEqual(len(buy), 3)

    def test_full_holdings_replace(self):
        """满仓：卖出最低分"""
        buy, sell = self._call(['D', 'E'], topk=3, n_drop=1)
        self.assertIn('E', sell)

    def test_holdings_without_score(self):
        """持仓无预测分数：优先卖出"""
        buy, sell = self._call(['X'], topk=3, n_drop=1)
        self.assertIn('X', sell)

    def test_n_drop_exceeds_holdings(self):
        """n_drop 超过持仓数"""
        buy, sell = self._call(['A'], topk=3, n_drop=5)
        self.assertLessEqual(len(sell), 1)


if __name__ == "__main__":
    unittest.main()
