import threading
import time


class HealthChecker:
    """健康检查器"""
    
    def __init__(self, trading_system, alert_func=None):
        self.trading_system = trading_system
        self.alert_func = alert_func
        self.running = False
        self.check_interval = 60  # 每分钟检查
    
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._check_loop, daemon=True)
        self.thread.start()
        print("🏥 健康检查已启动")
    
    def stop(self):
        self.running = False
    
    def _check_loop(self):
        while self.running:
            self._do_check()
            time.sleep(self.check_interval)
    
    def _do_check(self):
        issues = []
        if not self._check_connection():
            issues.append("交易连接异常")
        if not self._check_heartbeat():
            issues.append("心跳超时")
        if not self._check_memory():
            issues.append("内存使用过高")
        
        if issues and self.alert_func:
            self.alert_func("健康检查异常", "\n".join(issues))
    
    def _check_connection(self):
        """连接检查：尝试查询资产"""
        try:
            asset = self.trading_system.trader.query_stock_asset(
                self.trading_system.acc
            )
            return asset is not None
        except:
            return False
    
    def _check_heartbeat(self):
        """心跳检查：5 分钟内有活动"""
        last = getattr(self.trading_system, 'last_activity', 0)
        return time.time() - last < 300
    
    def _check_memory(self):
        """内存检查：< 500 MB"""
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        return memory_mb < 500
        