"""
Picks Service
今日选股 / 昨日复盘
"""
from datetime import date, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd

from app.services.session_loader import session_loader


class PicksService:
    """选股服务"""
    
    def get_today_picks(self, preset: str = "all") -> Dict[str, Any]:
        """获取今日选股（BUY 信号）"""
        df = session_loader.load_daily_summary()
        
        if df.empty:
            return {"date": str(date.today()), "picks": []}
        
        # 获取最新日期
        date_col = '日期' if '日期' in df.columns else 'date'
        latest_date = df[date_col].max()
        
        # 过滤当天 BUY
        action_col = '决策' if '决策' in df.columns else 'action'
        today_df = df[(df[date_col] == latest_date) & (df[action_col] == 'BUY')]
        
        picks = []
        for _, row in today_df.iterrows():
            picks.append(self._row_to_pick(row))
        
        return {
            "date": latest_date,
            "picks": picks
        }
    
    def get_yesterday_recap(self, preset: str = "all") -> Dict[str, Any]:
        """获取昨日复盘（已完成交易）"""
        trades_df = session_loader.load_trades_summary()
        
        if trades_df.empty:
            return {"date": None, "trades": []}
        
        # 获取最新日期
        date_col = '日期' if '日期' in trades_df.columns else 'date'
        latest_date = trades_df[date_col].max()
        
        # 过滤当天交易
        day_trades = trades_df[trades_df[date_col] == latest_date]
        
        trades = []
        for _, row in day_trades.iterrows():
            trades.append(self._row_to_trade(row))
        
        return {
            "date": latest_date,
            "trades": trades,
            "summary": self._calc_summary(trades)
        }
    
    def _row_to_pick(self, row) -> Dict:
        """将 DataFrame 行转为 pick 对象"""
        return {
            "symbol": row.get('股票') or row.get('symbol', 'N/A'),
            "action": row.get('决策') or row.get('action', 'WAIT'),
            "reason": row.get('决策理由') or row.get('decision_reason', ''),
            "or15_close": self._safe_float(row.get('OR15收盘价') or row.get('or15_close')),
            "entry_price": self._safe_float(row.get('开仓价格') or row.get('entry_price')),
            "max_potential_pct": self._safe_float(row.get('最大潜在收益') or row.get('max_potential_pct'))
        }
    
    def _row_to_trade(self, row) -> Dict:
        """将 DataFrame 行转为 trade 对象"""
        return {
            "symbol": row.get('股票') or row.get('symbol', 'N/A'),
            "entry_price": self._safe_float(row.get('开仓价格') or row.get('entry_price')),
            "exit_price": self._safe_float(row.get('卖出价格') or row.get('exit_price')),
            "pnl_pct": self._parse_pct(row.get('收益率') or row.get('pnl_pct')),
            "exit_reason": row.get('出场原因') or row.get('exit_reason', ''),
            "holding_time": row.get('持仓时间') or row.get('holding_time', '')
        }
    
    def _calc_summary(self, trades: List[Dict]) -> Dict:
        """计算交易汇总"""
        if not trades:
            return {"total": 0, "wins": 0, "losses": 0, "win_rate": 0, "total_pnl_pct": 0}
        
        pnls = [t["pnl_pct"] for t in trades]
        wins = sum(1 for p in pnls if p > 0)
        
        return {
            "total": len(trades),
            "wins": wins,
            "losses": len(trades) - wins,
            "win_rate": round(wins / len(trades), 3) if trades else 0,
            "total_pnl_pct": round(sum(pnls), 2)
        }
    
    def _safe_float(self, val) -> float:
        if pd.isna(val) or val is None:
            return 0.0
        if isinstance(val, str):
            val = val.replace('$', '').replace(',', '').replace('%', '').strip()
            try:
                return float(val)
            except:
                return 0.0
        return float(val)
    
    def _parse_pct(self, val) -> float:
        if pd.isna(val) or val is None:
            return 0.0
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            val = val.replace('%', '').replace('+', '').strip()
            try:
                return float(val)
            except:
                return 0.0
        return 0.0


# 全局实例
picks_service = PicksService()
