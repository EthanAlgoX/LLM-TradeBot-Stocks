"""
Session Loader Service
读取最新回测 session 数据
"""
import os
import json
import pandas as pd
from datetime import datetime, date
from typing import Optional, Dict, List, Any
from pathlib import Path


class SessionLoader:
    """加载回测 session 数据"""
    
    def __init__(self, base_path: str = None):
        if base_path is None:
            # 默认路径：相对于 server 目录
            base_path = os.path.join(
                os.path.dirname(__file__), 
                "..", "..", "..", 
                "data", "backtest_results"
            )
        self.base_path = Path(base_path).resolve()
    
    def get_latest_session(self) -> Optional[str]:
        """获取最新的 session 目录名"""
        if not self.base_path.exists():
            return None
        
        sessions = sorted([
            d.name for d in self.base_path.iterdir() 
            if d.is_dir() and d.name[0].isdigit()
        ], reverse=True)
        
        return sessions[0] if sessions else None
    
    def get_session_path(self, session: str = None) -> Optional[Path]:
        """获取 session 目录路径"""
        if session is None:
            session = self.get_latest_session()
        if session is None:
            return None
        return self.base_path / session
    
    def load_daily_summary(self, session: str = None) -> pd.DataFrame:
        """加载 daily_summary.csv"""
        session_path = self.get_session_path(session)
        if session_path is None:
            return pd.DataFrame()
        
        csv_path = session_path / "daily_summary.csv"
        if not csv_path.exists():
            return pd.DataFrame()
        
        return pd.read_csv(csv_path, encoding='utf-8-sig')
    
    def load_trades_summary(self, session: str = None) -> pd.DataFrame:
        """加载 trades_summary.csv"""
        session_path = self.get_session_path(session)
        if session_path is None:
            return pd.DataFrame()
        
        # 找到 trades_summary 文件
        for f in session_path.iterdir():
            if f.name.startswith("trades_summary") and f.suffix == ".csv":
                return pd.read_csv(f, encoding='utf-8-sig')
        
        return pd.DataFrame()
    
    def load_traded_stocks_summary(self, session: str = None) -> Dict[str, Any]:
        """加载 traded_stocks_summary.json"""
        session_path = self.get_session_path(session)
        if session_path is None:
            return {}
        
        json_path = session_path / "traded_stocks_summary.json"
        if not json_path.exists():
            return {}
        
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def load_day_records(self, trade_date: date, session: str = None) -> List[Dict]:
        """加载某一天的所有股票记录"""
        session_path = self.get_session_path(session)
        if session_path is None:
            return []
        
        date_str = trade_date.strftime("%Y-%m-%d")
        day_path = session_path / date_str
        
        if not day_path.exists():
            return []
        
        records = []
        for f in day_path.iterdir():
            if f.suffix == ".json":
                with open(f, 'r', encoding='utf-8') as file:
                    records.append(json.load(file))
        
        return records
    
    def get_trading_days(self, session: str = None) -> List[str]:
        """获取 session 中的所有交易日"""
        session_path = self.get_session_path(session)
        if session_path is None:
            return []
        
        days = []
        for d in session_path.iterdir():
            if d.is_dir() and d.name[0].isdigit():
                days.append(d.name)
        
        return sorted(days, reverse=True)


# 全局实例
session_loader = SessionLoader()
