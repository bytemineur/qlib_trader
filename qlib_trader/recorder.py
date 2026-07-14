import pandas as pd
from pathlib import Path
from datetime import datetime

class PortfolioRecorder:
    def __init__(self, xt_trader, acc):
        self.xt_trader = xt_trader
        self.acc = acc
        # 项目根目录/logs
        self.data_dir = Path(__file__).parent.parent / 'logs'
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def record_daily_snapshot(self, date_str=None):
        '''记录当日资金、持仓、成交，日期格式: YYYY-MM-DD'''
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
        trade_date = date_str.replace('-', '')  # miniQMT 用 'YYYYMMDD'

        # 1. 资金
        asset = self.xt_trader.query_stock_asset(self.acc)
        if asset:
            daily_row = {
                'date': date_str,
                'account_type': asset.account_type,
                'account_id': asset.account_id,
                'cash': asset.cash,
                'frozen_cash': asset.frozen_cash,
                'market_value': asset.market_value,
                'total_asset': asset.total_asset,  
            }
            self._append_df(pd.DataFrame([daily_row]), 'portfolio_daily.csv')

        # 2. 持仓
        positions = self.xt_trader.query_stock_positions(self.acc)
        if positions:
            pos_list = []
            for pos in positions:
                pos_list.append({
                    'date': date_str,
                    'account_type': pos.account_type,
                    'account_id': pos.account_id,
                    'stock_code': pos.stock_code,
                    'volume': pos.volume,
                    'can_use_volume': pos.can_use_volume,
                    'open_price': pos.open_price,
                    'market_value': pos.market_value,
                    'frozen_volume': pos.frozen_volume,
                    'on_road_volume': pos.on_road_volume,
                    'yesterday_volume': pos.yesterday_volume,
                    'avg_price': pos.avg_price,
                    'direction': pos.direction,
                })
            self._append_df(pd.DataFrame(pos_list), 'positions_daily.csv')

        # 3. 当日成交（不传时间即当日）
        trades = self.xt_trader.query_stock_trades(self.acc)
        if trades:
            trade_list = []
            for t in trades:
                trade_list.append({
                    'date': date_str,
                    'account_type': t.account_type,
                    'account_id': t.account_id,
                    'stock_code': t.stock_code,
                    'order_type': t.order_type,
                    'traded_id': t.traded_id,
                    'traded_time': t.traded_time,
                    'traded_price': t.traded_price,
                    'traded_volume': t.traded_volume,
                    'traded_amount': t.traded_amount,
                    'order_id': t.order_id,
                    'order_sysid': t.order_sysid,
                    'strategy_name': t.strategy_name,
                    'order_remark': t.order_remark,
                    'direction': t.direction,
                    'offset_flag': t.offset_flag,
                })
            self._append_df(pd.DataFrame(trade_list), 'trades.csv')

    def _append_df(self, df_new, filename):
        """追加DataFrame到CSV，若文件不存在则创建并写入表头"""
        filepath = self.data_dir / filename
        if filepath.exists():
            df_new.to_csv(filepath, mode='a', header=False, index=False)
        else:
            df_new.to_csv(filepath, mode='w', header=True, index=False)
            