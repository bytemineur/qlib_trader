from datetime import datetime, time as dt_time
import time
import schedule
import threading
from chinese_calendar import is_workday

class TradingScheduler:
    """交易时间调度器"""
    
    def __init__(self, trading_system):
        self.trading_system = trading_system
        self.running = False
    
    def is_trading_day(self):
        """判断今天是否为交易日（基于中国法定工作日）"""
        return is_workday(datetime.now())
    
    def is_trading_time(self):
        """是否在交易时段"""
        if not self.is_trading_day():
            return False
        now = datetime.now().time()
        return (dt_time(9, 30) <= now<= dt_time(11, 30)
                or dt_time(13, 0) <= now<= dt_time(15, 0))
    
    def start(self):
        self.running = True
        # 9:25 启动（提前 5 分钟）
        schedule.every().day.at("09:25").do(self._start_trading)
        # 15:05 停止（延后 5 分钟，等成交回报）
        schedule.every().day.at("15:05").do(self._stop_trading)
        # 15:10 发日报
        schedule.every().day.at("15:10").do(self._send_daily_report)

        # 如果启动时已在交易时段，立即触发启动（不依赖 9:25 定时触发）
        if self.is_trading_time():
            self._start_trading()
        
        # 如果启动时已在交易时段，立即触发启动（不依赖 9:25 定时触发）
        if self.is_trading_time():
            self._start_trading()
        
        self.thread = threading.Thread(target=self._run_schedule, daemon=True)
        self.thread.start()
        print("📅 交易调度器已启动")
    
    def stop(self):
        self.running = False
    
    def _run_schedule(self):
        while self.running:
            schedule.run_pending()
            time.sleep(1)
    
    def _start_trading(self):
        if self.is_trading_day():
            print(f"[{datetime.now()}] 开始交易")
            self.trading_system.start()
    
    def _stop_trading(self):
        print(f"[{datetime.now()}] 停止交易")
        self.trading_system.stop()
    
    def _send_daily_report(self):
        if self.is_trading_day():
            print(f"[{datetime.now()}] 发送交易日报")
            self.trading_system.send_daily_report()
            