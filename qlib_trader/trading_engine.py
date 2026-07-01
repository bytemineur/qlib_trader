import threading
import time
import uuid
from collections import deque
from queue import PriorityQueue, Empty
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, List

from xtquant import xtconstant


class SignalType(Enum):
    """信号类型枚举"""
    BUY = 1
    SELL = 2

@dataclass
class TradeSignal:
    """交易信号数据类（支持优先级队列比较）"""
    signal_id: str
    signal_type: SignalType
    stock_code: str
    price: float
    volume: int
    strategy: str
    reason: str
    timestamp: datetime
    priority: int = 0

    def __lt__(self, other: 'TradeSignal') -> bool:
        """优先级队列比较方法（按优先级降序，同优先级按时间戳升序）"""
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.timestamp < other.timestamp

class SignalQueue:
    """自定义信号队列（包装 PriorityQueue，增加历史记录）"""
    def __init__(self, maxsize: int = 0):
        self._queue = PriorityQueue(maxsize=maxsize)
        self._history = deque(maxlen=1000)  # 保存最近1000条

    def put(self, signal: TradeSignal) -> None:
        self._queue.put(signal)
        self._history.append(signal)

    def get(self, block: bool = True, timeout: float = None) -> TradeSignal:
        return self._queue.get(block, timeout)

    def get_nowait(self) -> TradeSignal:
        return self._queue.get_nowait()

    def qsize(self) -> int:
        return self._queue.qsize()

    def empty(self) -> bool:
        return self._queue.empty()

    def clear(self) -> None:
        """清空队列"""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except Empty:
                break

    def get_history(self, n: int = 10) -> List[TradeSignal]:
        """获取最近的 n 条历史信号"""
        return list(self._history)[-n:]

class SignalProducer:
    """信号生产者基类"""

    def __init__(self, signal_queue: SignalQueue) -> None:
        self.queue = signal_queue
        self.running = False
        self.strategy_name = "BaseStrategy"
        self.thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """启动生产者线程"""
        self.running = True
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        print(f"🔔 策略启动: {self.strategy_name}")

    def stop(self) -> None:
        """停止生产者"""
        self.running = False

    def _run(self) -> None:
        """策略主循环（子类可重写）"""
        while self.running:
            try:
                self._generate_signals()
            except Exception as e:
                print(f"策略异常: {e}")
            time.sleep(1)

    def _generate_signals(self) -> None:
        """生成信号（由子类实现）"""
        pass

    def emit_signal(
        self,
        signal_type: SignalType,
        stock_code: str,
        price: float,
        volume: int,
        reason: str,
        priority: int = 0
    ) -> None:
        """发送信号到队列"""
        signal = TradeSignal(
            signal_id=str(uuid.uuid4())[:8],
            signal_type=signal_type,
            stock_code=stock_code,
            price=price,
            volume=volume,
            strategy=self.strategy_name,
            reason=reason,
            timestamp=datetime.now(),
            priority=priority,
        )
        self.queue.put(signal)
        print(f"📤 发送信号: {signal}")

class SignalConsumer:
    """信号消费者（执行交易）"""

    def __init__(
        self,
        signal_queue: SignalQueue,
        trader: Any,
        acc: Any
    ) -> None:
        self.queue = signal_queue
        self.trader = trader
        self.acc = acc
        self.running = False
        self.executed_count = 0
        self.failed_count = 0
        self.thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """启动消费者线程"""
        self.running = True
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        print("⚡ 执行器启动")

    def stop(self) -> None:
        """停止消费者"""
        self.running = False

    def _run(self) -> None:
        """消费循环"""
        while self.running:
            try:
                signal = self.queue.get(timeout=1)
                if signal is not None:
                    self._execute_signal(signal)
            except Empty:
                continue  # 超时无信号，继续循环

    def _execute_signal(self, signal: TradeSignal) -> None:
        """执行信号（买入/卖出）"""
        print(f"📥 执行信号: {signal}")
        try:
            if signal.signal_type == SignalType.BUY:
                self._execute_buy(signal)
            elif signal.signal_type == SignalType.SELL:
                self._execute_sell(signal)
            self.executed_count += 1
        except Exception as e:
            print(f"❌ 执行失败: {e}")
            self.failed_count += 1

    def _execute_buy(self, signal: TradeSignal) -> None:
        """执行买入委托"""
        order_id = self.trader.order_stock(
            self.acc,
            signal.stock_code,
            xtconstant.STOCK_BUY,
            signal.volume,
            xtconstant.FIX_PRICE,
            signal.price,
            signal.strategy,
            signal.reason,
        )
        print(f"买入委托: {order_id}")

    def _execute_sell(self, signal: TradeSignal) -> None:
        """执行卖出委托（检查可用持仓）"""
        pos = self.trader.query_stock_position(self.acc, signal.stock_code)
        if not pos or pos.can_use_volume <= 0:
            print("无可卖持仓")
            return
        volume = min(signal.volume, pos.can_use_volume)
        order_id = self.trader.order_stock(
            self.acc,
            signal.stock_code,
            xtconstant.STOCK_SELL,
            volume,
            xtconstant.FIX_PRICE,
            signal.price,
            signal.strategy,
            signal.reason,
        )
        print(f"卖出委托: {order_id}")

class TradingEngine:
    """交易引擎：管理所有生产者和消费者"""

    def __init__(self, trader: Any, acc: Any) -> None:
        self.trader = trader
        self.acc = acc
        self.last_activity = time.time()
        self.signal_queue = SignalQueue()
        self.producers: List[SignalProducer] = []
        self.consumer = SignalConsumer(self.signal_queue, trader, acc)

    def add_strategy(self, producer: SignalProducer) -> None:
        """添加一个策略生产者"""
        self.producers.append(producer)

    def start(self) -> None:
        """启动引擎（先启动消费者，再启动所有生产者）"""
        self.consumer.start()
        for producer in self.producers:
            producer.start()
        print("🚀 交易引擎已启动")

    def stop(self) -> None:
        """停止引擎（先停止生产者，再停止消费者）"""
        for producer in self.producers:
            producer.stop()
        self.consumer.stop()
        print("交易引擎已停止")

    def get_stats(self) -> dict:
        """获取引擎运行统计信息"""
        return {
            'queue_size': self.signal_queue.qsize(),
            'executed': self.consumer.executed_count,
            'failed': self.consumer.failed_count,
        }
    
    def send_daily_report(self):
        """发送交易日报（暂用统计信息替代）"""
        stats = self.get_stats()
        report = f"""
========== 交易日报 ==========
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
队列待处理: {stats['queue_size']}
已执行信号: {stats['executed']}
失败信号: {stats['failed']}
==============================="""
        print(report)          # 或使用 logger.info()
