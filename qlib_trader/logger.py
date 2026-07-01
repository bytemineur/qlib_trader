import os
import time
import threading
import schedule
import logging
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from xtquant.xttrader import XtQuantTraderCallback


def setup_logger(name='trading', log_dir='logs'):
    """配置日志器，默认将日志放在项目根目录下的 logs/"""
    if log_dir is None:
        project_root = Path(__file__).parent.parent
        log_dir = project_root / 'logs'
    else:
        log_dir = Path(log_dir)
    
    # 按日期命名文件
    os.makedirs(log_dir, exist_ok=True)
    log_file = log_dir / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # 文件 handler：所有级别都写
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    # 控制台 handler：只看 INFO 及以上
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

class TradingLogger:
    """交易日志封装：分文件存"""
    
    def __init__(self, log_dir='logs'):
        self.logger = setup_logger('trading', log_dir)        # 主日志
        self.order_logger = setup_logger('orders', log_dir)   # 委托日志
        self.signal_logger = setup_logger('signals', log_dir) # 信号日志
    
    def log_signal(self, strategy, stock_code, signal_type, reason):
        """信号日志"""
        self.signal_logger.info(
            f"[{strategy}] {signal_type.upper()} {stock_code} | {reason}"
        )
    
    def log_order(self, order_id, stock_code, direction, volume, price, status):
        """委托日志"""
        self.order_logger.info(
            f"委托{order_id} | {direction} {stock_code} | "
            f"{volume}股@{price} | {status}"
        )
    
    def log_trade(self, order_id, stock_code, volume, price, amount):
        """成交日志"""
        self.order_logger.info(
            f"成交{order_id} | {stock_code} | "
            f"{volume}股@{price} | 金额={amount:.2f}"
        )
    
    def log_error(self, error_type, message, detail=None):
        """错误日志"""
        self.logger.error(f"[{error_type}] {message}")
        if detail:
            self.logger.error(f"  详情: {detail}")
    
    def log_position(self, positions):
        """持仓快照"""
        self.logger.info("="*40)
        self.logger.info("持仓快照:")
        for pos in positions:
            self.logger.info(
                f"  {pos.stock_code}: {pos.volume}股 "
                f"成本={pos.avg_price:.2f} 盈亏={pos.float_profit:.2f}"
            )
        self.logger.info("="*40)

class LoggingCallback(XtQuantTraderCallback):
    """带日志的回调类"""
    
    def __init__(self, trading_logger):
        self.tl = trading_logger
    
    def on_disconnected(self):
        self.tl.log_error("CONNECTION", "与MiniQMT断开连接")
    
    def on_stock_order(self, order):
        status_map = {
            48: '未报', 49: '待报', 50: '已报',
            51: '已报待撤', 52: '部成待撤', 53: '部撤',
            54: '已撤', 55: '部成', 56: '已成', 57: '废单',
        }
        status = status_map.get(order.order_status, str(order.order_status))
        direction = '买入'if order.order_type == 23 else'卖出'
        
        self.tl.log_order(
            order.order_id, order.stock_code, direction,
            order.order_volume, order.price, status,
        )
    
    def on_stock_trade(self, trade):
        self.tl.log_trade(
            trade.order_id, trade.stock_code,
            trade.traded_volume, trade.traded_price, trade.traded_amount,
        )
    
    def on_order_error(self, error):
        self.tl.log_error(
            "ORDER_ERROR",
            f"委托{error.order_id}失败",
            error.error_msg,
        )
    
    def on_cancel_error(self, error):
        self.tl.log_error(
            "CANCEL_ERROR",
            f"撤单{error.order_id}失败",
            error.error_msg,
        )

class TradingMonitor:
    """交易监控"""
    
    def __init__(self):
        self.start_time = time.time()
        self.metrics = {
            'orders_total': 0,
            'orders_success': 0,
            'orders_failed': 0,
            'trades_total': 0,
            'trades_amount': 0,
            'signals_total': 0,
            'errors_total': 0,
        }
        self.stock_metrics = defaultdict(lambda: {
            'orders': 0, 'trades': 0, 'amount': 0,
        })
    
    def on_signal(self, stock_code):
        self.metrics['signals_total'] += 1
    
    def on_order(self, stock_code, success=True):
        self.metrics['orders_total'] += 1
        if success:
            self.metrics['orders_success'] += 1
        else:
            self.metrics['orders_failed'] += 1
        self.stock_metrics[stock_code]['orders'] += 1
    
    def on_trade(self, stock_code, amount):
        self.metrics['trades_total'] += 1
        self.metrics['trades_amount'] += amount
        self.stock_metrics[stock_code]['trades'] += 1
        self.stock_metrics[stock_code]['amount'] += amount
    
    def on_error(self):
        self.metrics['errors_total'] += 1
    
    def get_report(self):
        runtime = time.time() -self.start_time
        hours = runtime/3600
        
        report = f"""
========== 交易监控报告 ==========
运行时长: {hours:.2f}小时

【信号与委托】
  信号总数: {self.metrics['signals_total']}
  委托总数: {self.metrics['orders_total']}
  成功委托: {self.metrics['orders_success']}
  失败委托: {self.metrics['orders_failed']}
  成功率: {self.metrics['orders_success']/max(1,self.metrics['orders_total'])*100:.1f}%

【成交统计】
  成交笔数: {self.metrics['trades_total']}
  成交金额: {self.metrics['trades_amount']:,.2f}

【错误统计】
  错误次数: {self.metrics['errors_total']}

【分股票统计】
"""
        for code, m in self.stock_metrics.items():
            report += f"  {code}: 委托{m['orders']}笔, 成交{m['trades']}笔, 金额{m['amount']:,.0f}\n"
        report += "=================================="
        return report
    
    def print_report(self):
        print(self.get_report())

class ReportScheduler:
    """定时报告调度器"""
    
    def __init__(self, monitor, logger):
        self.monitor = monitor
        self.logger = logger
        self.running = False
    
    def start(self):
        self.running = True
        # 每小时报告
        schedule.every().hour.do(self._hourly_report)
        # 每天 15:05 收盘汇总
        schedule.every().day.at("15:05").do(self._daily_report)
        
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        print("📊 定时报告已启动")
    
    def stop(self):
        self.running = False
    
    def _run(self):
        while self.running:
            schedule.run_pending()
            time.sleep(1)
    
    def _hourly_report(self):
        report = self.monitor.get_report()
        self.logger.info(f"\n[小时报告]\n{report}")
    
    def _daily_report(self):
        report = self.monitor.get_report()
        self.logger.info(f"\n[每日汇总]\n{report}")
        # 这里可以调钉钉/飞书 webhook 推送
