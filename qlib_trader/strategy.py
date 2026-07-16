#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
strategy.py - TopkDropout 策略实现（中证全指指数增强）

日频策略：T日收盘生成预测分数，T+1日收盘前14:50调仓。
"""

import datetime
import traceback
from pathlib import Path

import pandas as pd
from xtquant import xtdata

from trading_engine import SignalProducer, SignalType

# 关闭 xtdata 的 hello 信息
xtdata.enable_hello = False


# ---------- 工具函数 ----------
def _convert_code(code: str) -> str:
    """
    将原始股票代码转换为 xtquant 可识别的格式。

    例如：'SH600000' -> '600000.SH'
    """
    if code.startswith('SH'):
        return code[2:] + '.SH'
    if code.startswith('SZ'):
        return code[2:] + '.SZ'
    if code.startswith('BJ'):
        return code[2:] + '.BJ'
    return code


# ---------- 策略类 ----------
class MyStrategy(SignalProducer):
    """TopkDropout 策略实现，基于预测分数进行调仓。"""

    def __init__(self, queue, xt_trader, acc, logger, alert):
        super().__init__(queue)

        self.strategy_name = "TopkDropoutStrategy_中证全指指数增强"
        self.topk = 250               # 目标持仓股票数量
        self.n_drop = 25              # 每次调仓卖出的数量
        self.cash = 20_000            # 每只股票的买入金额（元）
        self.last_rebalance_date = None  # 上次调仓日期（避免日内重复触发）

        self.xt_trader = xt_trader
        self.acc = acc
        self.logger = logger
        self.alert = alert

    # ==================== 核心调仓逻辑 ====================
    def _generate_signals(self):
        """
        生成买卖信号（由交易引擎定时调用）。

        调仓触发条件：
            - 当前时间为 14:50（下午）
            - 当日尚未调仓
        """
        now = datetime.datetime.now()

        # 判断是否在 14:50 且今日未调仓
        if (now.hour == 14 and now.minute == 50) and self.last_rebalance_date != now.date():
            self.logger.info(f"[调仓] 当前时间：{now.strftime('%H:%M:%S')} 开始执行调仓...")

            try:
                # -------- 1. 读取预测分数 --------
                csv_path = Path(__file__).parent.parent / 'ml' / 'pred_score.csv'
                df = pd.read_csv(csv_path)
                df['instrument'] = df['instrument'].apply(_convert_code)
                pred_score = df.set_index('instrument')['score'].squeeze()

                # -------- 2. 剔除风险股票 --------
                risk_codes = [code for code in pred_score.index if self._is_risk_stock(code)]
                if risk_codes:
                    self.logger.info(f"从预测分数中剔除风险股票: {risk_codes}")
                    pred_score = pred_score.drop(index=risk_codes)

                # -------- 3. 获取当前持仓 --------
                positions = self.xt_trader.query_stock_positions(self.acc)
                holdings = [pos.stock_code for pos in positions if pos.volume != 0]

                # -------- 4. 计算调仓列表 --------
                buy_list, sell_list = self._get_dropout_trade_list(
                    pred_score, holdings, self.topk, self.n_drop
                )

                # 输出调仓信息
                self.logger.info(
                    f"预测分数 Top{self.topk}：\n"
                    f"{pred_score.sort_values(ascending=False).head(self.topk)}"
                )
                self.logger.info(
                    f"持仓数: {len(holdings)}, 买入: {len(buy_list)}, 卖出: {len(sell_list)}"
                )
                self.logger.info(f"持仓: {holdings}")
                self.logger.info(f"买入: {buy_list}")
                self.logger.info(f"卖出: {sell_list}")

                # -------- 5. 获取实时行情 --------
                price_info = xtdata.get_full_tick(buy_list + sell_list)

                # -------- 6. 执行卖出 --------
                for stock in sell_list:
                    # 获取卖一价（买一价）
                    current_price = price_info[stock]['bidPrice'][0]
                    if current_price <= 0:
                        self.logger.info(f"股票 {stock} 无有效买一价，跳过卖出")
                        continue

                    position = self.xt_trader.query_stock_position(self.acc, stock)
                    current_volume = position.volume

                    self.emit_signal(
                        signal_type=SignalType.SELL,
                        stock_code=stock,
                        price=current_price,
                        volume=current_volume,
                        reason="Qlib_ML_Strategy",
                        priority=1
                    )
                    self.alert.alert_trade(
                        stock, "卖出", current_volume, current_price,
                        current_volume * current_price
                    )

                # -------- 7. 执行买入 --------
                for stock in buy_list:
                    # 获取卖一价
                    order_price = price_info[stock]['askPrice'][0]
                    if order_price <= 0:
                        self.logger.info(f"股票 {stock} 无有效卖一价，跳过买入")
                        continue

                    # 科创板最小交易单位 200 股，其他 100 股
                    unit = 200 if stock.startswith('688') else 100
                    order_volume = round((self.cash / order_price) / unit) * unit
                    if order_volume == 0:
                        order_volume = unit  # 至少买入 1 手

                    self.emit_signal(
                        signal_type=SignalType.BUY,
                        stock_code=stock,
                        price=order_price,
                        volume=order_volume,
                        reason="Qlib_ML_Strategy",
                        priority=0
                    )
                    self.alert.alert_trade(
                        stock, "买入", order_volume, order_price,
                        order_volume * order_price
                    )

                # 更新调仓日期
                self.last_rebalance_date = now.date()
                self.logger.info("调仓完成")

            except Exception:
                self.logger.error(f"调仓异常:\n{traceback.format_exc()}")

    # ==================== 核心算法 ====================
    def _get_dropout_trade_list(self, pred_score, current_holdings, topk, n_drop):
        """
        计算买入和卖出列表（支持持仓股无预测分数的情况）。

        参数
        ----------
        pred_score : pd.Series
            预测分数，索引为股票代码，值为分数（分数越高越看好）。
        current_holdings : list
            当前持仓的股票代码列表。
        topk : int
            目标持仓数量。
        n_drop : int
            本次最多卖出的数量。

        返回
        -------
        buy_list : list
            本次需要买入的股票代码。
        sell_list : list
            本次需要卖出的股票代码。
        """
        # 1. 清理预测分数
        pred_score = pred_score.dropna()
        all_stocks = set(pred_score.index)
        if not all_stocks:
            return [], []

        # 为无分数股票设定一个极低的默认分数（排在末尾）
        default_score = pred_score.min() - 1

        def get_score(stock):
            """返回股票分数，若无则返回默认低分。"""
            return pred_score.get(stock, default_score)

        # 2. 当前持仓按分数降序排列（无分数者排最后）
        last = current_holdings[:]              # 复制列表
        last_sorted = sorted(last, key=lambda x: get_score(x), reverse=True)
        last_set = set(last)

        # 3. 候选买入池：有分数且当前未持有的股票
        candi = [s for s in all_stocks if s not in last_set]
        candi_sorted = sorted(candi, key=lambda x: pred_score[x], reverse=True)

        # 4. 今日可买入数量（补足 topk 并替换卖出的股票）
        n_today = n_drop + topk - len(last)
        n_today = max(n_today, 0)
        today = candi_sorted[:n_today]

        # 5. 合并当前持仓与今日买入，整体排序
        comb_all = last_sorted + today
        comb_sorted = sorted(comb_all, key=lambda x: get_score(x), reverse=True)

        # 6. 确定卖出：从排序后的尾部（分数最低）取出 n_drop 个，且必须为原有持仓
        n_drop_actual = min(n_drop, len(comb_sorted))
        bottom_n = comb_sorted[-n_drop_actual:] if n_drop_actual > 0 else []
        sell_list = [s for s in bottom_n if s in last_set]

        # 7. 确定买入：根据卖出数量和目标仓位计算
        n_buy = len(sell_list) + topk - len(last)
        n_buy = max(n_buy, 0)
        buy_list = today[:n_buy]

        return buy_list, sell_list

    # ==================== 风险判断 ====================
    def _is_risk_stock(self, stock_code: str) -> bool:
        """
        判断股票是否为风险股（ST、*ST、退市、停牌等）。

        若满足以下任一条件则返回 True（应被剔除）：
            - 查询不到股票详情（可能已退市）
            - 名称包含 'ST', '*ST', '退'
            - InstrumentStatus != 0（非正常交易状态）

        异常时默认返回 True（安全优先）。
        """
        try:
            info = xtdata.get_instrument_detail(stock_code, iscomplete=False)
            if info is None:
                return True

            name = info.get('InstrumentName', '')
            if any(kw in name for kw in ['ST', '*ST', '退']):
                return True

            if info.get('InstrumentStatus', 0) != 0:
                return True

            return False

        except Exception:
            # 发生异常时也视为风险股，避免异常股票进入交易
            return True