"""
test_trading_engine.py — 交易引擎核心模块测试用例
"""
import sys
from unittest.mock import MagicMock

# Mock xtquant 模块（Windows 专有，WSL 不可用）
sys.modules['xtquant'] = MagicMock()
sys.modules['xtquant.xtconstant'] = MagicMock()
sys.modules['xtquant.xttrader'] = MagicMock()
sys.modules['xtquant.xttype'] = MagicMock()

# 设置必要的常量
import xtquant.xtconstant as xtc
xtc.STOCK_BUY = 23
xtc.STOCK_SELL = 24
xtc.FIX_PRICE = 11

import unittest
import time
from unittest.mock import Mock, MagicMock as MM, patch
from datetime import datetime
from queue import Empty

sys.path.insert(0, "/mnt/c/Users/zhh/Desktop/qlib_trader/qlib_trader")



# ============================================================================
# TradeSignal & SignalType
# ============================================================================

class TestSignalType(unittest.TestCase):
    """SignalType 枚举测试"""

    def test_buy_value(self):
        from trading_engine import SignalType
        self.assertEqual(SignalType.BUY.value, 1)

    def test_sell_value(self):
        from trading_engine import SignalType
        self.assertEqual(SignalType.SELL.value, 2)


class TestTradeSignal(unittest.TestCase):
    """TradeSignal 数据类测试"""

    def test_create_signal(self):
        from trading_engine import TradeSignal, SignalType
        ts = datetime.now()
        signal = TradeSignal(
            signal_id="abc123",
            signal_type=SignalType.BUY,
            stock_code="000001.SZ",
            price=10.5,
            volume=100,
            strategy="Test",
            reason="test",
            timestamp=ts,
            priority=5,
        )
        self.assertEqual(signal.stock_code, "000001.SZ")
        self.assertEqual(signal.priority, 5)

    def test_priority_ordering(self):
        """验证 __lt__ 行为：priority 越小越"小"（PriorityQueue 中先出）"""
        from trading_engine import TradeSignal, SignalType
        now = datetime.now()
        low_pri = TradeSignal("a", SignalType.BUY, "s", 1, 1, "t", "r", now, priority=0)
        high_pri = TradeSignal("b", SignalType.BUY, "s", 1, 1, "t", "r", now, priority=10)

        # 注意：源码中 __lt__ 返回 self.priority < other.priority
        # 因此 priority=0 小于 priority=10，低 priority 先出队
        self.assertTrue(low_pri < high_pri)  # low_pri 先出

    def test_same_priority_time_ordering(self):
        """同优先级按时间排序：先产生的先出"""
        from trading_engine import TradeSignal, SignalType
        early = TradeSignal("a", SignalType.BUY, "s", 1, 1, "t", "r",
                            datetime(2026, 1, 1, 9, 30), priority=0)
        late = TradeSignal("b", SignalType.BUY, "s", 1, 1, "t", "r",
                           datetime(2026, 1, 1, 10, 0), priority=0)
        self.assertTrue(early < late)


# ============================================================================
# SignalQueue
# ============================================================================

class TestSignalQueue(unittest.TestCase):
    """SignalQueue 测试"""

    def setUp(self):
        from trading_engine import SignalQueue
        self.queue = SignalQueue()

    def _make_signal(self, stock="000001.SZ", priority=0):
        from trading_engine import TradeSignal, SignalType
        return TradeSignal(
            signal_id="test", signal_type=SignalType.BUY,
            stock_code=stock, price=10, volume=100,
            strategy="s", reason="r", timestamp=datetime.now(),
            priority=priority
        )

    def test_put_and_get(self):
        """入队和出队"""
        s = self._make_signal()
        self.queue.put(s)
        self.assertEqual(self.queue.qsize(), 1)
        self.assertFalse(self.queue.empty())
        result = self.queue.get_nowait()
        self.assertEqual(result.stock_code, "000001.SZ")

    def test_empty_queue_get_nowait_raises(self):
        """空队列 get_nowait 抛 Empty"""
        with self.assertRaises(Empty):
            self.queue.get_nowait()

    def test_get_with_timeout(self):
        """超时出队"""
        with self.assertRaises(Empty):
            self.queue.get(timeout=0.01)

    def test_clear(self):
        """清空队列"""
        self.queue.put(self._make_signal())
        self.queue.put(self._make_signal("600519.SH"))
        self.queue.clear()
        self.assertTrue(self.queue.empty())

    def test_history_records(self):
        """历史记录保存"""
        s1 = self._make_signal("A.SZ")
        s2 = self._make_signal("B.SH")
        self.queue.put(s1)
        self.queue.put(s2)
        history = self.queue.get_history(2)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].stock_code, "A.SZ")
        self.assertEqual(history[1].stock_code, "B.SH")

    def test_history_bound(self):
        """历史记录有上限（deque maxlen=1000）"""
        for i in range(1100):
            self.queue.put(self._make_signal(f"{i:06d}.SZ"))
        history = self.queue.get_history(1100)
        self.assertLessEqual(len(history), 1000)  # deque 自动截断

    def test_priority_ordering_in_queue(self):
        """优先级排序行为：当前实现是低 priority 先出队"""
        from trading_engine import TradeSignal, SignalType
        now = datetime.now()
        low = TradeSignal("l", SignalType.BUY, "s", 1, 1, "t", "r", now, priority=0)
        high = TradeSignal("h", SignalType.BUY, "s", 1, 1, "t", "r", now, priority=10)
        mid = TradeSignal("m", SignalType.BUY, "s", 1, 1, "t", "r", now, priority=5)

        self.queue.put(high)
        self.queue.put(mid)
        self.queue.put(low)

        # 当前代码行为：priority=0 先出 → priority=5 → priority=10
        self.assertEqual(self.queue.get_nowait().signal_id, "l")
        self.assertEqual(self.queue.get_nowait().signal_id, "m")
        self.assertEqual(self.queue.get_nowait().signal_id, "h")


# ============================================================================
# SignalProducer
# ============================================================================

class TestSignalProducer(unittest.TestCase):
    """SignalProducer 基类测试"""

    def setUp(self):
        from trading_engine import SignalQueue, SignalProducer
        self.queue = SignalQueue()
        self.producer = SignalProducer(self.queue)

    def test_default_strategy_name(self):
        """默认策略名"""
        self.assertEqual(self.producer.strategy_name, "BaseStrategy")

    def test_emit_signal(self):
        """emit_signal 将信号入队"""
        from trading_engine import SignalType
        self.producer.strategy_name = "Test"
        self.producer.emit_signal(
            SignalType.BUY, "000001.SZ", 10.5, 100, "reason", priority=5
        )
        signal = self.queue.get_nowait()
        self.assertEqual(signal.stock_code, "000001.SZ")
        self.assertEqual(signal.priority, 5)
        self.assertEqual(signal.strategy, "Test")
        self.assertIn("reason", signal.reason)

    def test_start_stop(self):
        """启动和停止"""
        self.producer.start()
        self.assertTrue(self.producer.running)
        time.sleep(0.1)
        self.producer.stop()
        self.assertFalse(self.producer.running)


# ============================================================================
# SignalConsumer (with mock trader)
# ============================================================================

class TestSignalConsumer(unittest.TestCase):
    """SignalConsumer 测试"""

    def setUp(self):
        from trading_engine import SignalQueue, SignalConsumer
        self.queue = SignalQueue()
        self.mock_trader = MagicMock()
        self.mock_acc = MagicMock()
        self.consumer = SignalConsumer(self.queue, self.mock_trader, self.mock_acc)

    def test_start_stop(self):
        """启动和停止"""
        self.consumer.start()
        self.assertTrue(self.consumer.running)
        time.sleep(0.1)
        self.consumer.stop()
        self.assertFalse(self.consumer.running)

    def test_execute_buy(self):
        """买入委托调用 trader.order_stock"""
        from trading_engine import TradeSignal, SignalType
        from xtquant import xtconstant

        signal = TradeSignal(
            "test", SignalType.BUY, "000001.SZ", 10.5, 100,
            "strat", "reason", datetime.now(), priority=0
        )

        self.consumer._execute_buy(signal)
        self.mock_trader.order_stock.assert_called_once()
        call_args = self.mock_trader.order_stock.call_args[0]
        self.assertEqual(call_args[1], "000001.SZ")
        self.assertEqual(call_args[2], xtconstant.STOCK_BUY)
        self.assertEqual(call_args[3], 100)
        self.assertEqual(call_args[4], xtconstant.FIX_PRICE)
        self.assertEqual(call_args[5], 10.5)

    def test_execute_buy_increments_count(self):
        """成功买入计数增加"""
        from trading_engine import TradeSignal, SignalType

        signal = TradeSignal(
            "test", SignalType.BUY, "000001.SZ", 10.5, 100,
            "s", "r", datetime.now(), priority=0
        )
        self.consumer._execute_signal(signal)
        self.assertEqual(self.consumer.executed_count, 1)
        self.assertEqual(self.consumer.failed_count, 0)

    def test_execute_failure_increments_failed_count(self):
        """失败买入失败计数增加"""
        from trading_engine import TradeSignal, SignalType

        self.mock_trader.order_stock.side_effect = Exception("fail")
        signal = TradeSignal(
            "test", SignalType.BUY, "000001.SZ", 10.5, 100,
            "s", "r", datetime.now(), priority=0
        )
        self.consumer._execute_signal(signal)
        self.assertEqual(self.consumer.failed_count, 1)

    def test_execute_sell_no_position(self):
        """无可卖持仓时跳过"""
        from trading_engine import TradeSignal, SignalType

        # query_stock_position 返回 None（无持仓）
        self.mock_trader.query_stock_position.return_value = None

        signal = TradeSignal(
            "test", SignalType.SELL, "000001.SZ", 10.5, 100,
            "s", "r", datetime.now(), priority=0
        )
        self.consumer._execute_sell(signal)
        # 不应调用 order_stock
        self.mock_trader.order_stock.assert_not_called()

    def test_execute_sell_with_position(self):
        """有持仓时卖出"""
        from trading_engine import TradeSignal, SignalType
        from xtquant import xtconstant

        mock_pos = Mock()
        mock_pos.can_use_volume = 200
        self.mock_trader.query_stock_position.return_value = mock_pos

        signal = TradeSignal(
            "test", SignalType.SELL, "000001.SZ", 10.5, 500,  # 尝试卖500
            "s", "r", datetime.now(), priority=0
        )
        self.consumer._execute_sell(signal)

        call_args = self.mock_trader.order_stock.call_args[0]
        self.assertEqual(call_args[2], xtconstant.STOCK_SELL)
        self.assertEqual(call_args[3], 200)  # 被限制为可用持仓200

    def test_execute_sell_zero_available(self):
        """可用持仓为0时跳过"""
        from trading_engine import TradeSignal, SignalType

        mock_pos = Mock()
        mock_pos.can_use_volume = 0
        self.mock_trader.query_stock_position.return_value = mock_pos

        signal = TradeSignal(
            "test", SignalType.SELL, "000001.SZ", 10.5, 100,
            "s", "r", datetime.now(), priority=0
        )
        self.consumer._execute_sell(signal)
        self.mock_trader.order_stock.assert_not_called()


# ============================================================================
# TradingEngine
# ============================================================================

class TestTradingEngine(unittest.TestCase):
    """TradingEngine 测试"""

    def setUp(self):
        from trading_engine import TradingEngine
        self.mock_trader = MagicMock()
        self.mock_acc = MagicMock()
        self.engine = TradingEngine(self.mock_trader, self.mock_acc)

    def test_add_strategy(self):
        """添加策略"""
        from trading_engine import SignalProducer
        producer = SignalProducer(self.engine.signal_queue)
        self.engine.add_strategy(producer)
        self.assertIn(producer, self.engine.producers)

    def test_get_stats_initial(self):
        """初始统计"""
        stats = self.engine.get_stats()
        self.assertEqual(stats["queue_size"], 0)
        self.assertEqual(stats["executed"], 0)
        self.assertEqual(stats["failed"], 0)

    def test_last_activity_set(self):
        """last_activity 初始值"""
        self.assertGreater(self.engine.last_activity, 0)

    def test_start_stop(self):
        """启动和停止引擎"""
        self.engine.start()
        self.assertTrue(self.engine.consumer.running)
        time.sleep(0.1)
        self.engine.stop()
        self.assertFalse(self.engine.consumer.running)


if __name__ == "__main__":
    unittest.main()
