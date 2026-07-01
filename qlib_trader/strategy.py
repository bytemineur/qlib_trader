"""
strategy.py - 测试策略（示例）
"""
import math
import datetime
import traceback
import pandas as pd
from pathlib import Path

from xtquant import xtdata
xtdata.enable_hello = False

from trading_engine import SignalProducer, SignalType

class MyStrategy(SignalProducer):
    """策略实现"""
    
    def __init__(self, queue, xt_trader, acc, logger, alert):
        super().__init__(queue)
        self.strategy_name = "TopkDropoutStrategy_中证全指指数增强" # 日频策略，T日收盘生成预测分数，T+1日收盘前14:50调仓
        self.topk = 250  # 持仓数量
        self.n_drop = 25  # 每次调仓卖出数量
        self.cash = 20_000  # 每只股票买入金额
        self.last_rebalance_date = None  # 上次调仓日期
        self.xt_trader = xt_trader
        self.acc = acc
        self.logger = logger
        self.alert = alert
    
    def _generate_signals(self):
        # 检查调仓时间（14:50-14:51 触发，每日一次）
        now = datetime.datetime.now()
        if (now.hour == 14 and now.minute == 50) and self.last_rebalance_date != now.date():
            self.logger.info(f"[调仓] 当前时间：{now.strftime('%H:%M:%S')} 开始执行调仓...")
            try:
                # 读取预测分数，pred_score.csv默认在项目根目录的 ml 文件夹下
                csv_path = Path(__file__).parent.parent / 'ml' / 'pred_score.csv'
                df = pd.read_csv(csv_path)
                def convert_code(code):
                    if code.startswith('SH'):
                        return code[2:] + '.SH'
                    elif code.startswith('SZ'):
                        return code[2:] + '.SZ'
                    elif code.startswith('BJ'):
                        return code[2:] + '.BJ'
                    else:
                        return code
                df['instrument'] = df['instrument'].apply(convert_code)
                pred_score = df.set_index('instrument')['score'].squeeze()

                positions = self.xt_trader.query_stock_positions(self.acc)
                holdings = [pos.stock_code for pos in positions]
                
                buy_list, sell_list = self._get_dropout_trade_list(pred_score, holdings, self.topk, self.n_drop)
                self.logger.info(f"预测分数：{pred_score.sort_values(ascending=False).head(self.topk)}")
                self.logger.info(f"持仓列表长度: {len(holdings)}，买入列表长度: {len(buy_list)}，卖出列表长度: {len(sell_list)}")
                self.logger.info(f"持仓: {holdings}")
                self.logger.info(f"买入: {buy_list}")
                self.logger.info(f"卖出: {sell_list}")

                # 执行调仓
                price_info = xtdata.get_full_tick(buy_list + sell_list)
                for stock in sell_list:
                    position = self.xt_trader.query_stock_position(self.acc, stock)
                    if position.stock_code == stock:
                        current_volume = position.volume
                        current_price = price_info[stock]['bidPrice'][0]
                    self.emit_signal(
                        signal_type=SignalType.SELL,
                        stock_code=stock,
                        price=current_price,
                        volume=current_volume,
                        reason="Qlib_ML_Strategy",
                        priority=1
                        )
                    self.alert.alert_trade(stock, "卖出", current_volume, current_price, current_volume * current_price)
                
                for stock in buy_list:
                    order_price = price_info[stock]['askPrice'][0]
                    if order_price <= 0 or order_price > 300:
                        self.logger.info(f"股票 {stock} 无有效卖一价或价格大于300元，跳过买入")
                        continue
                    order_volume = math.round((self.cash / order_price) / 100) * 100 # 按 100 股整数倍下单，四舍五入
                    self.emit_signal(
                        signal_type=SignalType.BUY,
                        stock_code=stock,
                        price=order_price,
                        volume=order_volume,
                        reason="Qlib_ML_Strategy",
                        priority=0
                        )
                    self.alert.alert_trade(stock, "买入", order_volume, order_price, order_volume * order_price)
                self.last_rebalance_date = now.date()
                self.logger.info("调仓完成")
            except Exception as e:
                self.logger.error(f"调仓异常:\n{traceback.format_exc()}")

    def _get_dropout_trade_list(self, pred_score, current_holdings, topk, n_drop):
        """
        支持持仓股无预测分数的 TopkDropout 策略
        """
        # 1. 清理预测分数
        pred_score = pred_score.dropna()
        all_stocks = set(pred_score.index)
        if len(all_stocks) == 0:
            return [], []

        # 为无分数股票设定一个极低的默认分数（确保它们排在最末尾）
        default_score = pred_score.min() - 1

        def get_score(stock):
            """返回股票分数，若无则返回默认低分"""
            return pred_score.get(stock, default_score)

        # 2. 当前持仓（全部保留，无论有无分数），按分数降序排列
        last = current_holdings[:]                 # 复制列表
        last_sorted = sorted(last, key=lambda x: get_score(x), reverse=True)
        last_set = set(last)

        # 3. 候选买入池：仅包含有分数且未持有的股票
        candi = [s for s in all_stocks if s not in last_set]
        candi_sorted = sorted(candi, key=lambda x: pred_score[x], reverse=True)

        # 4. 今日可买入数量（补仓 + 替换卖出部分）
        n_today = n_drop + topk - len(last)
        if n_today < 0:
            n_today = 0
        today = candi_sorted[:n_today]

        # 5. 合并当前持仓与今日买入，按分数排序
        comb_all = last_sorted + today
        comb_sorted = sorted(comb_all, key=lambda x: get_score(x), reverse=True)

        # 6. 确定卖出：从组合尾部（分数最低）取出 n_drop 个，且必须属于原有持仓
        n_drop_actual = min(n_drop, len(comb_sorted))
        bottom_n = comb_sorted[-n_drop_actual:] if n_drop_actual > 0 else []
        sell_list = [s for s in bottom_n if s in last_set]

        # 7. 确定买入：根据卖出数量和目标仓位计算
        n_buy = len(sell_list) + topk - len(last)
        if n_buy < 0:
            n_buy = 0
        buy_list = today[:n_buy]

        return buy_list, sell_list