"""
Performance Service
计算 7 日滚动收益、胜率等 KPI
"""
from datetime import date, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd

from app.services.session_loader import session_loader


class PerformanceService:
    """收益计算服务"""
    
    def get_rolling_performance(
        self, 
        days: int = 7, 
        preset: str = "all"
    ) -> Dict[str, Any]:
        """
        获取滚动 N 日收益数据
        
        Returns:
            {
                "as_of": "2026-01-11",
                "window_days": 7,
                "kpi": {...},
                "daily": [...]
            }
        """
        # 加载数据
        df = session_loader.load_daily_summary()
        trades_df = session_loader.load_trades_summary()
        
        if df.empty:
            return self._empty_response(days)
        
        # 获取最近 N 个交易日
        trading_days = session_loader.get_trading_days()[:days]
        
        if not trading_days:
            return self._empty_response(days)
        
        # 计算每日收益
        daily_data = []
        total_trades = 0
        total_wins = 0
        
        for day_str in trading_days:
            # 尝试匹配日期列
            day_trades = pd.DataFrame()
            if not trades_df.empty:
                if '日期' in trades_df.columns:
                    day_trades = trades_df[trades_df['日期'] == day_str]
                elif 'date' in trades_df.columns:
                    day_trades = trades_df[trades_df['date'] == day_str]
            
            trades_count = len(day_trades)
            
            # 计算当日收益
            if trades_count > 0:
                # 解析收益率列
                pnl_col = None
                for col in ['收益率', 'pnl_pct', 'PnL%']:
                    if col in day_trades.columns:
                        pnl_col = col
                        break
                
                if pnl_col:
                    pnls = day_trades[pnl_col].apply(self._parse_pct)
                    daily_return = pnls.sum()
                    wins = (pnls > 0).sum()
                else:
                    daily_return = 0
                    wins = 0
                
                total_trades += trades_count
                total_wins += wins
                
                # 找最佳/最差
                if pnl_col and len(pnls) > 0:
                    max_idx = pnls.idxmax()
                    min_idx = pnls.idxmin()
                    
                    symbol_col = '股票' if '股票' in day_trades.columns else 'symbol'
                    
                    top_winner = {
                        "symbol": day_trades.loc[max_idx, symbol_col] if symbol_col in day_trades.columns else "N/A",
                        "pnl_pct": float(pnls.max()) / 100
                    }
                    top_loser = {
                        "symbol": day_trades.loc[min_idx, symbol_col] if symbol_col in day_trades.columns else "N/A",
                        "pnl_pct": float(pnls.min()) / 100
                    }
                else:
                    top_winner = None
                    top_loser = None
            else:
                daily_return = 0
                wins = 0
                top_winner = None
                top_loser = None
            
            daily_data.append({
                "date": day_str,
                "daily_return": daily_return / 100,  # 转为小数
                "trades": trades_count,
                "win_rate": wins / trades_count if trades_count > 0 else 0,
                "top_winner": top_winner,
                "top_loser": top_loser
            })
        
        # 倒序（最早在前）计算累计收益
        daily_data.reverse()
        cum_return = 0
        for d in daily_data:
            cum_return += d["daily_return"]
            d["cum_return"] = cum_return
        
        # 再倒回来（最新在前）
        daily_data.reverse()
        
        # 计算 KPI
        total_return = sum(d["daily_return"] for d in daily_data)
        avg_daily = total_return / len(daily_data) if daily_data else 0
        win_rate = total_wins / total_trades if total_trades > 0 else 0
        
        return {
            "as_of": trading_days[0] if trading_days else str(date.today()),
            "window_days": days,
            "kpi": {
                "total_return_pct": round(total_return * 100, 2),
                "avg_daily_return_pct": round(avg_daily * 100, 2),
                "win_rate": round(win_rate, 3),
                "total_trades": total_trades
            },
            "daily": daily_data
        }
    
    def _parse_pct(self, val) -> float:
        """解析百分比字符串"""
        if pd.isna(val):
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
    
    def _empty_response(self, days: int) -> Dict[str, Any]:
        return {
            "as_of": str(date.today()),
            "window_days": days,
            "kpi": {
                "total_return_pct": 0,
                "avg_daily_return_pct": 0,
                "win_rate": 0,
                "total_trades": 0
            },
            "daily": []
        }


# 全局实例
performance_service = PerformanceService()
