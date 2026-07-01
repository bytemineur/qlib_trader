"""
main.py - 无人值守交易程序入口
"""

import time
import yaml
from pathlib import Path
from datetime import datetime

from xtquant.xttrader import XtQuantTrader
from xtquant.xttype import StockAccount

from logger import setup_logger, TradingLogger, LoggingCallback, TradingMonitor, ReportScheduler
from alert import TradingAlert, DingTalkBot
from scheduler import TradingScheduler
from health_checker import HealthChecker
from robust import RobustTrader
from trading_engine import TradingEngine
from strategy import MyStrategy


# 加载配置文件
def load_config():
    project_root = Path(__file__).parent.parent
    config_path = project_root / "configs" / "config.yaml"
    
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件未找到: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

CONFIG = load_config()

logger = setup_logger('main')

def main():
    logger.info("="*50)
    logger.info("无人值守交易系统启动")
    logger.info(f"时间：{datetime.now()}")
    logger.info("="*50)

    # 1. 启动定时报告
    tl = TradingLogger()
    monitor = TradingMonitor()
    rs = ReportScheduler(monitor, tl.logger)
    rs.start()

    # 2. 告警
    bot = DingTalkBot(CONFIG['dingtalk_webhook'], CONFIG['dingtalk_secret'])
    alert = TradingAlert(bot)
    alert.bot.send_text("🚀 交易系统启动")

    # 3. 交易连接
    trader = XtQuantTrader(CONFIG['qmt_path'], CONFIG['session_id'])
    trader.start()

    if trader.connect() != 0:
        logger.error("连接失败")
        alert.alert_error("CONNECT", "交易连接失败")
        raise Exception("连接失败")
    
    acc = StockAccount(CONFIG['account_id'])
    trader.subscribe(acc)
    logger.info("✅ 交易连接成功")

    callback = LoggingCallback(tl)
    trader.register_callback(callback)

    # 4. 交易引擎
    engine = TradingEngine(trader, acc)
    strategy = MyStrategy(engine.signal_queue, trader, acc, logger, alert)
    engine.add_strategy(strategy)

    # 5. 时间调度
    scheduler = TradingScheduler(engine)
    scheduler.start()

    # 6. 健康检查
    health = HealthChecker(engine, alert.alert_error)
    health.start()

    # 7. 主循环
    try:
        while True:
            time.sleep(60)
            engine.last_activity = time.time()
    except KeyboardInterrupt:
        logger.info("收到中断信号")
    finally:
        scheduler.stop()
        health.stop()
        engine.stop()
        trader.stop()
        rs.stop()
        alert.bot.send_text("⏹️ 交易系统停止")
        logger.info("程序退出")
        
if __name__ == '__main__':
    robust_trader = RobustTrader(main, max_retries=10, retry_interval=60)
    robust_trader.run()
