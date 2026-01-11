"""
Data Manager - 数据存储管理
============================

统一管理原始数据和回测结果的存储结构。

结构:
data/
├── raw_data/                    # 原始 OHLCV 数据（回测+实盘共用）
│   └── {date}/                  # 按日期分文件夹
│       └── {symbol}_{interval}.json  # 股票+周期
├── backtest_results/            # 回测结果
│   └── {session_time}/          # 回测时间
│       ├── daily_summary.csv    # 汇总报告
│       ├── trades_summary.csv   # 交易明细
│       └── {date}/              # 按日期
│           └── {symbol}.json    # 股票详情

Author: AI Trader Team
Date: 2026-01-11
"""

import os
import json
from datetime import date, datetime
from typing import Dict, List, Optional, Any
import pandas as pd


class DataManager:
    """
    数据存储管理器
    
    统一管理原始数据和回测结果的存储。
    """
    
    def __init__(self, base_dir: str = "data"):
        self.base_dir = base_dir
        self.raw_data_dir = os.path.join(base_dir, "raw_data")
        self.backtest_dir = os.path.join(base_dir, "backtest_results")
        
        # 确保目录存在
        os.makedirs(self.raw_data_dir, exist_ok=True)
        os.makedirs(self.backtest_dir, exist_ok=True)
    
    # =========================================
    # 原始数据存储
    # =========================================
    
    def save_raw_bars(
        self,
        symbol: str,
        interval: str,
        bars: List[Dict],
        trade_date: date
    ) -> str:
        """
        保存原始 K 线数据
        
        Args:
            symbol: 股票代码
            interval: 周期 (1d, 15m, etc)
            bars: K 线数据列表
            trade_date: 交易日期
            
        Returns:
            保存的文件路径
        """
        # 创建日期文件夹
        date_dir = os.path.join(self.raw_data_dir, str(trade_date))
        os.makedirs(date_dir, exist_ok=True)
        
        # 文件名: AAPL_15m.json
        filename = f"{symbol}_{interval}.json"
        filepath = os.path.join(date_dir, filename)
        
        # 准备数据
        data = {
            "symbol": symbol,
            "interval": interval,
            "date": str(trade_date),
            "saved_at": datetime.now().isoformat(),
            "bar_count": len(bars),
            "bars": bars
        }
        
        # 保存
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        return filepath
    
    def save_raw_dataframe(
        self,
        symbol: str,
        interval: str,
        df: pd.DataFrame,
        trade_date: date
    ) -> str:
        """
        保存 DataFrame 格式的原始数据
        """
        # 转换为 records 格式
        df_copy = df.copy()
        df_copy = df_copy.reset_index()
        
        # 处理时间戳
        for col in df_copy.columns:
            if df_copy[col].dtype == 'datetime64[ns]' or 'timestamp' in col.lower():
                df_copy[col] = df_copy[col].astype(str)
        
        bars = df_copy.to_dict('records')
        return self.save_raw_bars(symbol, interval, bars, trade_date)
    
    def load_raw_bars(
        self,
        symbol: str,
        interval: str,
        trade_date: date
    ) -> Optional[List[Dict]]:
        """
        加载原始 K 线数据
        """
        filepath = os.path.join(
            self.raw_data_dir,
            str(trade_date),
            f"{symbol}_{interval}.json"
        )
        
        if not os.path.exists(filepath):
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data.get("bars", [])
    
    # =========================================
    # 回测结果存储
    # =========================================
    
    def create_backtest_session(self) -> str:
        """
        创建新的回测会话目录
        
        Returns:
            会话目录路径
        """
        session_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        session_dir = os.path.join(self.backtest_dir, session_time)
        os.makedirs(session_dir, exist_ok=True)
        return session_dir
    
    def save_stock_result(
        self,
        session_dir: str,
        trade_date: date,
        symbol: str,
        result: Dict
    ) -> str:
        """
        保存单只股票的回测结果
        
        Args:
            session_dir: 会话目录
            trade_date: 交易日期
            symbol: 股票代码
            result: 回测结果字典，应包含:
                - symbol: 股票代码
                - trade_date: 日期
                - action: BUY/WAIT/SELL
                - decision_reason: 决策理由
                - or15_close: OR15 收盘价
                - entry_price: 开仓价格
                - exit_price: 卖出价格
                - pnl_pct: 收益率
                - exit_reason: 出场原因
                - day_high_after_or15: 当日 OR15 后最高价
                - max_potential_pct: 最大潜在收益率
                - traded: 是否交易
        """
        # 创建日期文件夹
        date_dir = os.path.join(session_dir, str(trade_date))
        os.makedirs(date_dir, exist_ok=True)
        
        # 文件路径
        filepath = os.path.join(date_dir, f"{symbol}.json")
        
        # 添加保存时间
        result['saved_at'] = datetime.now().isoformat()
        
        # 保存
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def save_summary_csv(
        self,
        session_dir: str,
        records: List[Dict],
        filename: str = "daily_summary.csv"
    ) -> str:
        """
        保存汇总 CSV
        """
        filepath = os.path.join(session_dir, filename)
        df = pd.DataFrame(records)
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        return filepath
    
    def get_session_dirs(self) -> List[str]:
        """
        获取所有回测会话目录
        """
        if not os.path.exists(self.backtest_dir):
            return []
        
        sessions = []
        for name in sorted(os.listdir(self.backtest_dir), reverse=True):
            path = os.path.join(self.backtest_dir, name)
            if os.path.isdir(path):
                sessions.append(path)
        
        return sessions


# 全局实例
data_manager = DataManager()


if __name__ == "__main__":
    # 测试
    dm = DataManager()
    
    print("📂 Data Manager 测试")
    print(f"  原始数据目录: {dm.raw_data_dir}")
    print(f"  回测结果目录: {dm.backtest_dir}")
    
    # 创建回测会话
    session = dm.create_backtest_session()
    print(f"  新建会话: {session}")
    
    # 保存测试数据
    test_result = {
        "symbol": "AAPL",
        "trade_date": "2026-01-11",
        "action": "BUY",
        "decision_reason": "强买入信号: Trend alignment positive",
        "or15_close": 250.00,
        "entry_price": 250.50,
        "exit_price": 255.00,
        "pnl_pct": 1.80,
        "exit_reason": "TAKE_PROFIT",
        "day_high_after_or15": 256.00,
        "max_potential_pct": 2.40,
        "traded": True
    }
    
    filepath = dm.save_stock_result(session, date.today(), "AAPL", test_result)
    print(f"  保存结果: {filepath}")
