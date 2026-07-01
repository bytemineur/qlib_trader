import sys
import time
import traceback
from datetime import datetime


class RobustTrader:
   """健壮的交易程序：异常自动重启"""
   
   def __init__(self, trader_func, max_retries=10, retry_interval=60):
       """
        :param trader_func: 交易主函数
        :param max_retries: 最大重试次数
        :param retry_interval: 重试间隔（秒）
        """
       self.trader_func = trader_func
       self.max_retries = max_retries
       self.retry_interval = retry_interval
       self.retry_count = 0
   
   def run(self):
        while self.retry_count < self.max_retries:
            try:
                print(f"[{datetime.now()}] 交易程序启动")
                self.trader_func()
                # 正常执行完毕，跳出循环
                break
            except KeyboardInterrupt:
                print("用户中断，退出程序")
                raise   # 重新抛出，让上层或 main 捕获
            except Exception as e:
                self.retry_count += 1
                print(f"[错误] 程序异常: {e}")
                print(traceback.format_exc())
                if self.retry_count < self.max_retries:
                    print(f"等待{self.retry_interval}秒后重试 ({self.retry_count}/{self.max_retries})")
                    time.sleep(self.retry_interval)
                else:
                    print("达到最大重试次数，程序退出")
                    self._send_alert("程序异常退出，已达最大重试次数")
                    sys.exit(1)
        print("程序正常退出")
   
   def _send_alert(self, message):
       # 发送钉钉/飞书告警
       print(f"[告警] {message}")
