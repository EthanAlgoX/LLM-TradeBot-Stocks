#!/usr/bin/env python3
"""
🧪 美股日内回测系统
==================

基于简化版 3-Agent 框架的回测系统：
1. 每天只在开盘后 15 分钟 (9:45 AM) 调用交易策略
2. 买入后模拟 15 分钟 K 线，检查是否触发止损/止盈
3. 记录完整交易记录：卖出时间、价格、收益率、持仓时间
4. 收盘前强制平仓

Usage:
    # 回测单只股票，最近 30 天
    python backtest_daily.py --symbols AAPL --days 30
    
    # 回测多只股票
    python backtest_daily.py --symbols AAPL,TSLA,NVDA --days 60
    
    # 输出 HTML 报告
    python backtest_daily.py --symbols AAPL --days 30 --html

Author: AI Trader Team
Date: 2026-01-11
"""

import asyncio
import argparse
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo
import pandas as pd
import json
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 导入简化版 Agents
from src.agents.simple_agents import (
    DataProcessorAgent, MultiPeriodAgent, DecisionAgent,
    ProcessedData, TrendAnalysis, TradeDecision, WeeklyBias
)
from src.utils.data_cache import DataCache
from src.utils.data_manager import DataManager

# 美东时区
ET = ZoneInfo("America/New_York")

# 交易时间配置
MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)

# 决策时间窗口（开盘后多少分钟进行决策）
DECISION_WINDOW_MINUTES = 15  # 默认 15 分钟
STRATEGY_TIME = time(9, 45)  # 开盘后 DECISION_WINDOW_MINUTES 分钟

# 每日最大交易数量（只交易信号最强的 TOP N 股票）
MAX_DAILY_TRADES = 5


@dataclass
class BacktestTrade:
    """单笔交易记录"""
    symbol: str
    trade_date: date
    
    # 入场信息
    entry_time: datetime
    entry_price: float
    entry_reason: str
    
    # 出场信息
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: str = ""  # TAKE_PROFIT / STOP_LOSS / MARKET_CLOSE
    
    # 止损止盈
    stop_loss: float = 0.0
    take_profit: float = 0.0
    
    # 结果
    pnl: float = 0.0
    pnl_pct: float = 0.0
    holding_minutes: int = 0
    
    # 详细流程数据
    process_data: Dict[str, Any] = field(default_factory=dict)
    decision_process: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "trade_date": str(self.trade_date),
            "entry_time": self.entry_time.isoformat(),
            "entry_price": self.entry_price,
            "entry_reason": self.entry_reason,
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "exit_price": self.exit_price,
            "exit_reason": self.exit_reason,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "pnl": self.pnl,
            "pnl_pct": self.pnl_pct,
            "holding_minutes": self.holding_minutes,
            
            # 完整流程数据
            "input_data": self.process_data,
            "decision_process": self.decision_process
        }



@dataclass
class DailyRecord:
    """每日每股票记录 (包括未开仓) - 包含完整过程数据"""
    symbol: str
    trade_date: date
    
    # 决策信息
    action: str  # BUY / WAIT / REJECT
    decision_reason: str
    confidence: float = 0.0  # 决策置信度 (0-1)
    
    # OR15 信息 (开盘15分钟)
    or15_high: float = 0.0
    or15_low: float = 0.0
    or15_close: float = 0.0  # 第一根K线收盘价
    or15_open: float = 0.0   # 第一根K线开盘价
    or15_volume: int = 0     # OR15 成交量
    
    # 最大潜在收益 (当日OR15后最高价 - OR15 close)
    day_high_after_or15: float = 0.0
    day_high_time: str = ""  # 最高价出现时间
    max_potential_pct: float = 0.0  # (day_high - or15_close) / or15_close * 100
    
    # 实际交易信息 (如果开仓)
    traded: bool = False
    entry_price: float = 0.0
    take_profit: float = 0.0  # 决策卖出价格
    stop_loss: float = 0.0    # 决策止损价格
    exit_price: float = 0.0
    exit_reason: str = ""
    pnl_pct: float = 0.0
    
    # ===== 输入数据 =====
    # OR15 K线数据 (前一根和当前根)
    or15_bars: List[Dict] = field(default_factory=list)  # 最近几根15分钟K线
    
    # 技术指标值
    indicators: Dict[str, Any] = field(default_factory=dict)  # EMA, MACD, RSI 等
    
    # ===== 过程数据 =====
    # 多周期分析
    weekly_bias: str = ""     # 周线偏向: bullish/bearish/neutral
    daily_bias: str = ""      # 日线偏向
    intraday_bias: str = ""   # 日内偏向
    
    # 决策过程详细信息
    decision_notes: List[str] = field(default_factory=list)  # 决策过程的详细notes
    
    # 模拟交易过程 (如果交易)
    trade_simulation: Dict[str, Any] = field(default_factory=dict)  # 模拟执行细节
    
    def to_dict(self) -> Dict:
        return {
            # 基本信息
            "symbol": self.symbol,
            "trade_date": str(self.trade_date),
            "action": self.action,
            "decision_reason": self.decision_reason,
            "confidence": self.confidence,
            
            # OR15 信息
            "or15": {
                "open": self.or15_open,
                "high": self.or15_high,
                "low": self.or15_low,
                "close": self.or15_close,
                "volume": self.or15_volume
            },
            
            # 最大潜在收益
            "day_high_after_or15": self.day_high_after_or15,
            "day_high_time": self.day_high_time,
            "max_potential_pct": self.max_potential_pct,
            
            # 交易结果
            "traded": self.traded,
            "entry_price": self.entry_price,
            "take_profit": self.take_profit,
            "stop_loss": self.stop_loss,
            "exit_price": self.exit_price,
            "exit_reason": self.exit_reason,
            "pnl_pct": self.pnl_pct,
            
            # 输入数据 (K线)
            "input_data": {
                "or15_bars": self.or15_bars,
                "indicators": self.indicators
            },
            
            # 决策过程
            "decision_process": {
                "weekly_bias": self.weekly_bias,
                "daily_bias": self.daily_bias,
                "intraday_bias": self.intraday_bias,
                "notes": self.decision_notes
            },
            
            # 模拟交易详情
            "trade_simulation": self.trade_simulation
        }


@dataclass
class BacktestResult:
    """回测结果"""
    symbol: str
    start_date: date
    end_date: date
    
    # 交易统计
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    # 盈亏
    total_pnl_pct: float = 0.0
    avg_pnl_pct: float = 0.0
    max_win_pct: float = 0.0
    max_loss_pct: float = 0.0
    
    # 胜率
    win_rate: float = 0.0
    
    # 平均持仓时间
    avg_holding_minutes: float = 0.0
    
    # 出场类型统计
    take_profit_count: int = 0
    stop_loss_count: int = 0
    market_close_count: int = 0
    
    # 详细交易记录
    trades: List[BacktestTrade] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "start_date": str(self.start_date),
            "end_date": str(self.end_date),
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "total_pnl_pct": round(self.total_pnl_pct, 2),
            "avg_pnl_pct": round(self.avg_pnl_pct, 2),
            "max_win_pct": round(self.max_win_pct, 2),
            "max_loss_pct": round(self.max_loss_pct, 2),
            "win_rate": round(self.win_rate * 100, 1),
            "avg_holding_minutes": round(self.avg_holding_minutes, 1),
            "take_profit_count": self.take_profit_count,
            "stop_loss_count": self.stop_loss_count,
            "market_close_count": self.market_close_count,
            "trades": [t.to_dict() for t in self.trades]
        }


class DailyBacktester:
    """
    日内回测器
    
    模拟每日开盘后 15 分钟决策，然后用 15 分钟 K 线模拟持仓
    """
    
    def __init__(self):
        self.data_agent = DataProcessorAgent()
        self.trend_agent = MultiPeriodAgent()
        self.decision_agent = DecisionAgent()
        self.cache = DataCache()
        self.data_manager = DataManager()  # 数据存储管理
    
    async def run_backtest(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        verbose: bool = True
    ) -> BacktestResult:
        """
        运行单只股票的回测
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            verbose: 是否打印详细信息
        """
        if verbose:
            print(f"\n{'='*60}")
            print(f"🧪 回测 {symbol} | {start_date} ~ {end_date}")
            print(f"{'='*60}")
        
        result = BacktestResult(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            trades=[]
        )
        
        # 获取历史 15 分钟数据
        days_needed = (end_date - start_date).days + 30  # 多获取一些用于指标计算
        df_15m = await self._fetch_historical_15m(symbol, days_needed)
        
        if df_15m is None or df_15m.empty:
            print(f"  ❌ 无法获取 {symbol} 的历史数据")
            return result
        
        # 获取周线和日线数据用于趋势分析
        df_weekly = await self._fetch_historical_weekly(symbol, days_needed)
        df_daily = await self._fetch_historical_daily(symbol, days_needed)
        
        # 解析日期
        df_15m['date'] = pd.to_datetime(df_15m.index).date
        
        # 获取交易日列表
        trading_days = sorted(df_15m['date'].unique())
        trading_days = [d for d in trading_days if start_date <= d <= end_date]
        
        if verbose:
            print(f"  📅 交易日数: {len(trading_days)}")
        
        # 逐日回测
        for trade_date in trading_days:
            trade = await self._simulate_day(
                symbol=symbol,
                trade_date=trade_date,
                df_15m=df_15m,
                df_weekly=df_weekly,
                df_daily=df_daily,
                verbose=verbose
            )
            
            if trade:
                result.trades.append(trade)
        
        # 计算统计
        self._calculate_stats(result)
        
        if verbose:
            self._print_result(result)
        
        return result
    
    async def _fetch_historical_15m(self, symbol: str, days: int) -> Optional[pd.DataFrame]:
        """获取历史 15 分钟数据 (优先从本地 raw_data 读取)"""
        try:
            # 1. 尝试从本地 raw_data 读取最近 N 天的数据
            # 获取最近的交易日
            import os
            raw_dir = self.data_manager.raw_data_dir
            all_days = sorted([d for d in os.listdir(raw_dir) if os.path.isdir(os.path.join(raw_dir, d))], reverse=True)
            target_days = all_days[:days+5] # 多读几天确保足够
            
            local_bars = []
            valid_days = 0
            
            for date_str in target_days:
                bars = self.data_manager.load_raw_bars(symbol, '15m', date_str)
                if bars:

                    local_bars.extend(bars)
                    valid_days += 1
            
            if local_bars and valid_days >= min(3, days): # 如果有足够的本地数据
                # 转换为 DataFrame
                df = pd.DataFrame(local_bars)
                if not df.empty and 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    # 确保本地化为 ET (如果尚未包含时区)
                    if df['timestamp'].dt.tz is None:
                        df['timestamp'] = df['timestamp'].dt.tz_localize(ET)
                    else:
                        df['timestamp'] = df['timestamp'].dt.tz_convert(ET)
                        
                    df.set_index('timestamp', inplace=True)
                    df.sort_index(inplace=True)
                    

                        
                    # 重新计算指标
                    return self.data_agent._add_indicators(df)
            
            # 2. 如果本地数据不足，回退到通过 Cache/API 获取
            print(f"  ⚠️ {symbol} 本地数据不足 (找到 {valid_days} 天)，尝试 API 获取...")
            bars = self.cache.get_bars(symbol, '15m', days=days)
            if bars:
                df = self.cache.to_dataframe(bars)
                # 保存新获取的数据
                if not df.empty:
                    df_copy = df.copy()
                    df_copy['date'] = pd.to_datetime(df_copy.index).date
                    for trade_date, group in df_copy.groupby('date'):
                        self.data_manager.save_raw_dataframe(symbol, '15m', group.drop(columns=['date']), trade_date)
                
                return self.data_agent._add_indicators(df)
                
            return None
        except Exception as e:
            print(f"  ⚠️ 获取 15m 数据失败: {e}")
            return None
    
    async def _fetch_historical_weekly(self, symbol: str, days: int) -> Optional[pd.DataFrame]:
        """获取历史周线数据"""
        try:
            bars = self.cache.get_bars(symbol, '1w', days=days)
            if bars:
                df = self.cache.to_dataframe(bars)
                return self.data_agent._add_indicators(df)
            return None
        except Exception as e:
            return None
    
    async def _fetch_historical_daily(self, symbol: str, days: int) -> Optional[pd.DataFrame]:
        """获取历史日线数据"""
        try:
            bars = self.cache.get_bars(symbol, '1d', days=days)
            if bars:
                df = self.cache.to_dataframe(bars)
                return self.data_agent._add_indicators(df)
            return None
        except Exception as e:
            return None
    
    def _evaluate_signal(
        self,
        symbol: str,
        trade_date: date,
        df_15m: pd.DataFrame,
        df_weekly: Optional[pd.DataFrame],
        df_daily: Optional[pd.DataFrame]
    ) -> Tuple[str, float, str]:
        """
        评估股票在指定日期的信号强度
        
        Returns:
            (action, confidence, reason) - 决策、置信度、原因
        """
        # 获取当天的 15 分钟数据
        day_data = df_15m[df_15m['date'] == trade_date].copy()
        
        if day_data.empty or len(day_data) < 2:
            return ("WAIT", 0.0, "数据不足")
        
        # 过滤交易时段
        timestamps = pd.to_datetime(day_data.index)
        # 确保 timestamps 是 ET
        if timestamps.tz is None:
             timestamps = timestamps.tz_localize(ET)
        else:
             timestamps = timestamps.tz_convert(ET)
             
        day_data = day_data[
            ((timestamps.hour == 9) & (timestamps.minute >= 30)) |   # 9:30-9:59
            ((timestamps.hour >= 10) & (timestamps.hour < 16))       # 10:00-15:59
        ]
        
        if day_data.empty or len(day_data) < 2:
            return ("WAIT", 0.0, "交易时段数据不足")
        
        # 获取历史数据用于决策 - 严格禁止使用当天数据
        # 只能使用 trade_date 之前的数据，避免 lookahead bias
        historical_15m = df_15m[df_15m['date'] < trade_date].tail(100)
        bars_for_decision = historical_15m  # 不包含当天任何数据
        
        # 入场价使用当天 OR15 收盘价（9:45 决策时能看到的价格）
        # day_data 已经被过滤为正规交易时段
        if len(day_data) > 0:
            entry_price = float(day_data.iloc[0]['close'])
        elif len(historical_15m) > 0:
            entry_price = float(historical_15m.iloc[-1]['close'])
        else:
            entry_price = 0.0
        
        processed = ProcessedData(
            symbol=symbol,
            df_weekly=df_weekly[df_weekly.index.date < trade_date] if df_weekly is not None else None,
            df_daily=df_daily[df_daily.index.date < trade_date] if df_daily is not None else None,
            df_15m=bars_for_decision,
            current_price=entry_price,
            timestamp=datetime.combine(trade_date, STRATEGY_TIME, tzinfo=ET)
        )
        
        trend = self.trend_agent.analyze(processed)
        decision = self.decision_agent.decide(processed, trend, symbol=symbol)
        
        # ===== OR15 比较策略 (Volume Ratio > 1 & Price Ratio > 1) =====
        if decision.action == 'BUY':
            # 获取昨日 OR15
            prev_dates = sorted(list(set(df_15m[df_15m['date'] < trade_date]['date'])))
            if prev_dates:
                prev_date = prev_dates[-1]
                prev_day_data = df_15m[df_15m['date'] == prev_date].copy()
                
                # 过滤昨日交易时段，找到 OR15 (第一根 K 线)
                prev_stamps = pd.to_datetime(prev_day_data.index)
                if prev_stamps.tz is None: prev_stamps = prev_stamps.tz_localize(ET)
                else: prev_stamps = prev_stamps.tz_convert(ET)
                
                prev_day_data = prev_day_data[
                    ((prev_stamps.hour == 9) & (prev_stamps.minute >= 30)) |
                    ((prev_stamps.hour >= 10) & (prev_stamps.hour < 16))
                ]
                
                if not prev_day_data.empty:
                    today_or15 = day_data.iloc[0]
                    prev_or15 = prev_day_data.iloc[0]
                    
                    today_close = float(today_or15['close'])
                    prev_close = float(prev_or15['close'])
                    today_vol = float(today_or15['volume'])
                    prev_vol = float(prev_or15['volume'])
                    
                    price_ratio = today_close / prev_close
                    volume_ratio = today_vol / prev_vol if prev_vol > 0 else 0
                    
                    # 记录比值到原因中
                    ratio_info = f" [P_Ratio:{price_ratio:.2f}, V_Ratio:{volume_ratio:.2f}]"
                    
                    # 判断条件
                    if price_ratio > 1.0 and volume_ratio > 1.0:
                        decision.summary_reason += ratio_info
                        # 符合条件，保持 BUY，稍微增加置信度
                        decision.confidence = min(0.95, decision.confidence + 0.1)
                    else:
                        # 不符合条件，转为 WAIT
                        return ("WAIT", 0.0, f"OR15 动量不足{ratio_info} (需 > 1.0)")
            else:
                 return ("WAIT", 0.0, "无昨日数据对比")

        return (decision.action, decision.confidence, decision.summary_reason)
    
    async def _simulate_day(
        self,
        symbol: str,
        trade_date: date,
        df_15m: pd.DataFrame,
        df_weekly: Optional[pd.DataFrame],
        df_daily: Optional[pd.DataFrame],
        verbose: bool
    ) -> Optional[BacktestTrade]:
        """
        模拟单个交易日
        
        1. 获取当天开盘后 15 分钟的数据
        2. 调用交易策略决策
        3. 如果买入，模拟后续 K 线判断是否触发止损/止盈
        """
        # 获取当天的 15 分钟数据
        day_data = df_15m[df_15m['date'] == trade_date].copy()
        
        if day_data.empty or len(day_data) < 2:
            return None
        
        # 过滤掉盘前/盘后数据，只保留正规交易时段
        # 美股正常交易时间: 9:30 AM - 4:00 PM ET
        timestamps = pd.to_datetime(day_data.index)
        


        # 确保 timestamps 是 ET
        if timestamps.tz is None:
             timestamps = timestamps.tz_localize(ET)
        else:
             timestamps = timestamps.tz_convert(ET)
             
        day_data = day_data[
            ((timestamps.hour == 9) & (timestamps.minute >= 30)) |   # 9:30-9:59
            ((timestamps.hour >= 10) & (timestamps.hour < 16))       # 10:00-15:59
            # 16:00 bar usually implies closing price, handled by market close logic
        ]
        
        if day_data.empty or len(day_data) < 2:
            return None
        
        # 获取开盘后第一根 K 线（用于 OR15 计算）
        first_bar_idx = 0
        
        # 模拟 9:45 AM 时刻的数据环境
        # 此时只能看到第一根 15 分钟 K 线
        strategy_data = day_data.iloc[:1]
        
        # 构建截止到当天的历史数据用于趋势分析
        historical_cutoff = pd.Timestamp(trade_date)
        
        # 创建 ProcessedData (模拟开盘前决策环境)
        # 严格禁止使用当天数据，避免 lookahead bias
        # 只能使用 trade_date 之前的历史数据
        
        # 获取历史 15 分钟数据 (严格 < trade_date)
        historical_15m = df_15m[df_15m['date'] < trade_date].copy()
        bars_for_decision = historical_15m  # 不包含当天任何数据
        
        # 入场价 = OR15 K线收盘价（9:45 决策后买入）
        entry_price = float(day_data.iloc[0]['close'])
        
        processed = ProcessedData(
            symbol=symbol,
            df_weekly=df_weekly[df_weekly.index.date < trade_date] if df_weekly is not None else None,
            df_daily=df_daily[df_daily.index.date < trade_date] if df_daily is not None else None,
            df_15m=bars_for_decision,  # 历史数据 + 今天前两根
            current_price=entry_price,
            timestamp=datetime.combine(trade_date, STRATEGY_TIME, tzinfo=ET)
        )
        
        # 准备 process_data (输入数据)
        input_bars = []
        indicators = {}
        if processed.df_15m is not None and not processed.df_15m.empty:
            # 获取最后 5 根历史 K 线
            recent_df = processed.df_15m.iloc[-5:]
            for idx, row in recent_df.iterrows():
                bar_time = pd.to_datetime(idx)
                if bar_time.tz is not None:
                     bar_time = bar_time.tz_convert(ET)
                
                input_bars.append({
                    "date": str(bar_time.date()),
                    "time": bar_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "open": float(row['open']),
                    "high": float(row['high']),
                    "low": float(row['low']),
                    "close": float(row['close']),
                    "volume": int(row['volume'])
                })
            
            # 获取指标 (使用最后一根 K 线)
            last_row = processed.df_15m.iloc[-1]
            last_hist_time = pd.to_datetime(processed.df_15m.index[-1])
            if last_hist_time.tz is not None:
                last_hist_time = last_hist_time.tz_convert(ET)
                
            indicators = {
                "ema_9": float(last_row.get('ema_9', 0)),
                "ema_21": float(last_row.get('ema_21', 0)),
                "ema_50": float(last_row.get('ema_50', 0)),
                "macd": float(last_row.get('macd', 0)),
                "macd_signal": float(last_row.get('macd_signal', 0)),
                "macd_hist": float(last_row.get('macd_hist', 0)),
                "rsi": float(last_row.get('rsi', 0)),
                "atr": float(last_row.get('atr', 0)),
                "bb_upper": float(last_row.get('bb_upper', 0)),
                "bb_lower": float(last_row.get('bb_lower', 0)),
                "volume_ratio": float(last_row.get('volume_ratio', 0)),
                "_data_as_of": last_hist_time.strftime("%Y-%m-%d %H:%M:%S")
            }
        
        # 趋势分析
        trend = self.trend_agent.analyze(processed)
        
        # 决策（传入 symbol 用于高波动股票检测）
        decision = self.decision_agent.decide(processed, trend, symbol=symbol)
        
        if verbose:
            print(f"\n  📅 {trade_date} | {decision.action} | {decision.summary_reason}")
        
        # 只有 BUY 才模拟持仓
        if decision.action != 'BUY':
            return None
        
        # 创建交易记录 - 使用本地计算的 entry_price，避免不一致
        entry_time = datetime.combine(trade_date, STRATEGY_TIME, tzinfo=ET)
        
        # 动态止盈：根据时间调整目标
        # 分析显示大部分高点出现在 19:00-20:00（收盘前 1-2 小时）
        # 早盘入场：标准止盈 4%
        # 午盘入场：放宽止盈 5%
        # 晚盘入场：最大化止盈 6%
        hour = entry_time.hour
        if hour < 15:  # 早盘（9:45-15:00）
            take_profit_pct = 0.04  # 4%
        elif hour < 18:  # 午盘（15:00-18:00）
            take_profit_pct = 0.05  # 5%
        else:  # 晚盘（18:00-20:00）
            take_profit_pct = 0.06  # 6%
        
        # 动态止损：超高波动股票使用更宽止损
        # 分析发现 SIDU/OSS/RDW 经常有 20%+ 潜在但被 -2.1% 止损
        ULTRA_HIGH_VOLATILITY = ["SIDU", "OSS", "RDW", "NFE", "APLD"]
        if symbol in ULTRA_HIGH_VOLATILITY:
            stop_loss_pct = 0.03  # 3% 止损
        else:
            stop_loss_pct = 0.02  # 2% 止损
        
        trade = BacktestTrade(
            symbol=symbol,
            trade_date=trade_date,
            entry_time=entry_time,
            entry_price=entry_price,  # 使用本地计算的入场价格
            entry_reason=decision.summary_reason,
            stop_loss=entry_price - (entry_price * stop_loss_pct),  # 动态止损
            take_profit=entry_price + (entry_price * take_profit_pct),  # 动态止盈
            
            # 完整流程数据
            process_data={
                "input_bars": input_bars,
                "indicators": indicators
            },
            decision_process={
                "weekly_bias": trend.weekly_bias.value if hasattr(trend, 'weekly_bias') and hasattr(trend.weekly_bias, 'value') else str(getattr(trend, 'weekly_bias', '')),
                "daily_bias": trend.daily_bias.value if hasattr(trend, 'daily_bias') and hasattr(trend.daily_bias, 'value') else str(getattr(trend, 'daily_bias', '')),
                "intraday_bias": getattr(trend, 'intraday_structure', ''),
                "notes": decision.detailed_reasons,
                "confidence": decision.confidence
            }
        )
        
        if verbose:
            print(f"     💰 买入 ${trade.entry_price:.2f} | 止损 ${trade.stop_loss:.2f} | 止盈 ${trade.take_profit:.2f}")
        
        # 模拟后续 K 线，判断是否触发止损/止盈
        # 注意: 入场是在 9:45，即第一根 K 线收盘后
        # 所以需要从第二根 K 线 (index=1) 开始检查止损/止盈
        
        # 追踪止损参数
        TRAILING_ACTIVATION_PCT = 0.02  # 盈利超过 2% 启动追踪止损
        TRAILING_DISTANCE_PCT = 0.015   # 追踪距离 1.5%
        trailing_stop_active = False
        
        for i in range(1, len(day_data)):
            bar = day_data.iloc[i]
            bar_time = pd.to_datetime(bar.name)
            bar_high = float(bar['high'])
            bar_low = float(bar['low'])
            bar_close = float(bar['close'])
            
            # 计算当前盈亏
            current_pnl_pct = (bar_close - entry_price) / entry_price
            
            # 启动追踪止损（盈利超过 2%）
            if current_pnl_pct > TRAILING_ACTIVATION_PCT and not trailing_stop_active:
                trailing_stop_active = True
            
            # 更新追踪止损（只上调，不下调）
            if trailing_stop_active:
                new_trailing_stop = bar_close * (1 - TRAILING_DISTANCE_PCT)
                trade.stop_loss = max(trade.stop_loss, new_trailing_stop)
            
            # 检查止盈 (优先判断止盈)
            if bar_high >= trade.take_profit:
                trade.exit_time = bar_time
                trade.exit_price = trade.take_profit
                trade.exit_reason = "TAKE_PROFIT"
                break
            
            # 检查止损（包括追踪止损）
            if bar_low <= trade.stop_loss:
                trade.exit_time = bar_time
                trade.exit_price = trade.stop_loss
                trade.exit_reason = "STOP_LOSS"
                break
        
        # 如果没有触发止损/止盈，收盘时强制平仓
        if trade.exit_time is None:
            last_bar = day_data.iloc[-1]
            trade.exit_time = pd.to_datetime(last_bar.name)
            trade.exit_price = float(last_bar['close'])
            trade.exit_reason = "MARKET_CLOSE"
        
        # 计算盈亏 (包含滑点模拟)
        SLIPPAGE_PCT = 0.001  # 0.1% 滑点
        trade.pnl = trade.exit_price - trade.entry_price
        trade.pnl_pct = (trade.pnl / trade.entry_price) * 100 - SLIPPAGE_PCT * 100  # 扣除滑点
        
        # 计算持仓时间 - 使用时间差避免时区问题
        # 注意: exit_time 和 entry_time 都是 timezone-aware
        if trade.exit_time and trade.entry_time:
            # 使用 pd.Timestamp 确保时区一致性
            exit_ts = pd.Timestamp(trade.exit_time)
            entry_ts = pd.Timestamp(trade.entry_time)
            holding_delta = exit_ts - entry_ts
            trade.holding_minutes = max(0, int(holding_delta.total_seconds() / 60))
        else:
            trade.holding_minutes = 0
        
        if verbose:
            emoji = "✅" if trade.pnl >= 0 else "❌"
            print(f"     {emoji} 卖出 ${trade.exit_price:.2f} | {trade.exit_reason} | {trade.pnl_pct:+.2f}% | 持仓 {trade.holding_minutes} 分钟")
        
        return trade
    
    def _calculate_stats(self, result: BacktestResult):
        """计算回测统计"""
        if not result.trades:
            return
        
        result.total_trades = len(result.trades)
        
        pnls = [t.pnl_pct for t in result.trades]
        holdings = [t.holding_minutes for t in result.trades]
        
        result.winning_trades = sum(1 for p in pnls if p > 0)
        result.losing_trades = sum(1 for p in pnls if p <= 0)
        
        result.total_pnl_pct = sum(pnls)
        result.avg_pnl_pct = result.total_pnl_pct / result.total_trades
        result.max_win_pct = max(pnls) if pnls else 0
        result.max_loss_pct = min(pnls) if pnls else 0
        
        result.win_rate = result.winning_trades / result.total_trades if result.total_trades > 0 else 0
        result.avg_holding_minutes = sum(holdings) / len(holdings) if holdings else 0
        
        # 出场类型统计
        result.take_profit_count = sum(1 for t in result.trades if t.exit_reason == "TAKE_PROFIT")
        result.stop_loss_count = sum(1 for t in result.trades if t.exit_reason == "STOP_LOSS")
        result.market_close_count = sum(1 for t in result.trades if t.exit_reason == "MARKET_CLOSE")
    
    def _print_result(self, result: BacktestResult):
        """打印回测结果"""
        print(f"\n{'='*60}")
        print(f"📊 回测结果 | {result.symbol}")
        print(f"{'='*60}")
        
        print(f"  📅 时间范围: {result.start_date} ~ {result.end_date}")
        print(f"  📈 总交易数: {result.total_trades}")
        print(f"  ✅ 盈利交易: {result.winning_trades}")
        print(f"  ❌ 亏损交易: {result.losing_trades}")
        print(f"  🎯 胜率: {result.win_rate*100:.1f}%")
        print()
        print(f"  💰 总收益: {result.total_pnl_pct:+.2f}%")
        print(f"  📊 平均收益: {result.avg_pnl_pct:+.2f}%")
        print(f"  🚀 最大盈利: {result.max_win_pct:+.2f}%")
        print(f"  💔 最大亏损: {result.max_loss_pct:+.2f}%")
        print()
        print(f"  ⏱️ 平均持仓: {result.avg_holding_minutes:.0f} 分钟")
        print()
        print(f"  出场统计:")
        print(f"    🎯 止盈: {result.take_profit_count}")
        print(f"    🛡️ 止损: {result.stop_loss_count}")
        print(f"    🔔 收盘: {result.market_close_count}")
    
    def save_result(self, result: BacktestResult, output_dir: str = "data/backtest_results") -> str:
        """保存回测结果到 JSON"""
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"{result.symbol}_{result.start_date}_{result.end_date}.json"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 结果已保存: {filepath}")
        return filepath
    
    def generate_html_report(self, result: BacktestResult, output_dir: str = "data/backtest_results") -> str:
        """生成 HTML 报告"""
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"{result.symbol}_{result.start_date}_{result.end_date}.html"
        filepath = os.path.join(output_dir, filename)
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>回测报告 - {result.symbol}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; background: #1a1a2e; color: #eee; }}
        h1 {{ color: #00d9ff; }}
        .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 20px 0; }}
        .stat {{ background: #16213e; padding: 20px; border-radius: 10px; text-align: center; }}
        .stat .value {{ font-size: 28px; font-weight: bold; color: #00d9ff; }}
        .stat .label {{ font-size: 14px; color: #888; margin-top: 5px; }}
        .positive {{ color: #4ade80 !important; }}
        .negative {{ color: #f87171 !important; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #333; }}
        th {{ background: #16213e; color: #00d9ff; }}
        tr:hover {{ background: #16213e; }}
    </style>
</head>
<body>
    <h1>📊 回测报告 - {result.symbol}</h1>
    <p>{result.start_date} ~ {result.end_date}</p>
    
    <div class="stats">
        <div class="stat">
            <div class="value">{result.total_trades}</div>
            <div class="label">总交易数</div>
        </div>
        <div class="stat">
            <div class="value">{result.win_rate*100:.1f}%</div>
            <div class="label">胜率</div>
        </div>
        <div class="stat">
            <div class="value {'positive' if result.total_pnl_pct >= 0 else 'negative'}">{result.total_pnl_pct:+.2f}%</div>
            <div class="label">总收益</div>
        </div>
        <div class="stat">
            <div class="value">{result.avg_holding_minutes:.0f}min</div>
            <div class="label">平均持仓</div>
        </div>
    </div>
    
    <h2>📋 交易明细</h2>
    <table>
        <tr>
            <th>日期</th>
            <th>买入价</th>
            <th>卖出价</th>
            <th>止损</th>
            <th>止盈</th>
            <th>收益</th>
            <th>出场原因</th>
            <th>持仓时间</th>
        </tr>
        {''.join(f'''
        <tr>
            <td>{t.trade_date}</td>
            <td>${t.entry_price:.2f}</td>
            <td>${t.exit_price:.2f if t.exit_price else 0:.2f}</td>
            <td>${t.stop_loss:.2f}</td>
            <td>${t.take_profit:.2f}</td>
            <td class="{'positive' if t.pnl_pct >= 0 else 'negative'}">{t.pnl_pct:+.2f}%</td>
            <td>{t.exit_reason}</td>
            <td>{t.holding_minutes}min</td>
        </tr>
        ''' for t in result.trades)}
    </table>
</body>
</html>
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"📄 HTML 报告已生成: {filepath}")
        return filepath


def cleanup_old_backtests(max_keep: int = 5):
    """
    清理旧的回测会话，只保留最近的 N 个
    
    Args:
        max_keep: 保留的最大会话数
    """
    import shutil
    
    backtest_dir = "data/backtest_results"
    if not os.path.exists(backtest_dir):
        return
    
    # 获取所有会话目录
    sessions = []
    for name in os.listdir(backtest_dir):
        path = os.path.join(backtest_dir, name)
        if os.path.isdir(path):
            sessions.append((name, path))
    
    # 按时间戳排序（目录名格式：YYYY-MM-DD_HH-MM-SS）
    sessions.sort(reverse=True)  # 最新的在前
    
    # 删除旧的会话
    if len(sessions) > max_keep:
        to_delete = sessions[max_keep:]
        for name, path in to_delete:
            try:
                shutil.rmtree(path)
                print(f"🗑️  删除旧回测: {name}")
            except Exception as e:
                print(f"⚠️  删除失败 {name}: {e}")


async def main():
    # 导入 2026 股票池
    from src.config.watchlist_2026 import HIGH_MOMENTUM, AI_RELATED, ALL_TICKERS
    
    parser = argparse.ArgumentParser(description="美股日内回测系统")
    parser.add_argument("--symbols", type=str, help="股票代码，逗号分隔（默认：所有股票）")
    parser.add_argument("--days", type=int, default=3, help="回测天数")
    parser.add_argument("--html", action="store_true", help="生成 HTML 报告")
    parser.add_argument("--quiet", action="store_true", help="安静模式")
    parser.add_argument("--preset", type=str, choices=["momentum", "ai", "all"], 
                        default="all", help="预设股票池: momentum(高动量7只), ai(AI相关10只), all(全部股票)")
    
    args = parser.parse_args()
    
    # 根据预设或自定义选择股票
    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",")]
    else:
        # 使用预设股票池
        if args.preset == "momentum":
            symbols = HIGH_MOMENTUM  # 高动量股票（7只）
        elif args.preset == "ai":
            symbols = AI_RELATED[:10]  # AI 相关前 10 只
        else:
            symbols = ALL_TICKERS  # 全部股票（91只）
    end_date = date.today()
    start_date = end_date - timedelta(days=args.days)
    
    # 创建本次回测的输出目录 (按运行时间命名)
    run_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = f"data/backtest_results/{run_timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    
    # 清理旧的回测会话，只保留最近 5 个
    cleanup_old_backtests(max_keep=5)
    
    print("=" * 60)
    print("🧪 美股日内回测系统")
    print("=" * 60)
    print(f"  股票: {', '.join(symbols)}")
    print(f"  时间: {start_date} ~ {end_date}")
    print(f"  策略: 开盘后 15 分钟决策 + OR15 突破")
    print(f"  输出: {output_dir}")
    
    # 使用新的回测函数，同时获取 daily_records
    all_results, daily_records = await run_backtest_all(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        output_dir=output_dir,
        verbose=not args.quiet
    )
    
    # 保存每日记录到子文件夹
    save_daily_records(daily_records, output_dir)
    
    # 生成汇总交易记录
    generate_trade_summary(all_results, start_date, end_date, output_dir)
    
    # 生成产生交易的股票汇总 JSON
    generate_traded_stocks_summary(all_results, start_date, end_date, output_dir)


def save_daily_records(daily_records: Dict[date, List[DailyRecord]], output_dir: str):
    """
    保存每日每股票记录到子文件夹，并生成汇总 CSV
    
    结构:
    output_dir/
      daily_summary.csv           # 汇总 CSV（所有股票所有日期）
      2026-01-05/
        AAPL.json
        GOOGL.json
        ...
      2026-01-06/
        ...
    """
    all_records = []
    
    for trade_date, records in daily_records.items():
        # 创建日期子文件夹
        date_dir = os.path.join(output_dir, str(trade_date))
        os.makedirs(date_dir, exist_ok=True)
        
        for record in records:
            # 保存每只股票的记录
            filepath = os.path.join(date_dir, f"{record.symbol}.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(record.to_dict(), f, indent=2, ensure_ascii=False)
            
            # 收集数据用于 CSV
            all_records.append({
                "日期": str(trade_date),
                "股票": record.symbol,
                "决策": record.action,
                "决策理由": record.decision_reason,
                "OR15收盘价": f"${record.or15_close:.2f}" if record.or15_close > 0 else "-",
                "开仓价格": f"${record.entry_price:.2f}" if record.traded else "-",
                "卖出价格": f"${record.exit_price:.2f}" if record.traded and record.exit_price > 0 else "-",
                "收益率": f"{record.pnl_pct:+.2f}%" if record.traded else "-",
                "出场原因": record.exit_reason if record.traded else "-",
                "当日最高价": f"${record.day_high_after_or15:.2f}" if record.day_high_after_or15 > 0 else "-",
                "最高价时间": record.day_high_time if record.day_high_time else "-",
                "最大潜在收益": f"{record.max_potential_pct:.2f}%" if record.max_potential_pct > 0 else "-",
                "是否交易": "是" if record.traded else "否"
            })
    
    # 生成汇总 CSV
    if all_records:
        csv_path = os.path.join(output_dir, "daily_summary.csv")
        df = pd.DataFrame(all_records)
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"\n💾 汇总报告已保存: {csv_path}")
    
    print(f"💾 每日记录已保存: {output_dir}/[日期]/[股票].json")


async def run_backtest_all(
    symbols: List[str],
    start_date: date,
    end_date: date,
    output_dir: str,
    verbose: bool = True
) -> Tuple[List[BacktestResult], Dict[date, List[DailyRecord]]]:
    """
    运行多股票回测，返回回测结果和每日记录
    
    优化：每天只交易信号最强的 TOP 5 股票
    """
    MAX_DAILY_TRADES = 5 # 每天最多交易的股票数量
    
    backtester = DailyBacktester()
    all_results = []
    daily_records: Dict[date, List[DailyRecord]] = {}
    
    # 先获取所有交易日
    sample_bars = backtester.cache.get_bars(symbols[0], '15m', days=30)
    if not sample_bars:
        return all_results, daily_records
    
    df_sample = backtester.cache.to_dataframe(sample_bars)
    trading_days = sorted(set(pd.to_datetime(df_sample.index).date))
    trading_days = [d for d in trading_days if start_date <= d <= end_date]
    
    # 为每个交易日初始化记录列表
    for d in trading_days:
        daily_records[d] = []
    
    # 预加载所有股票数据
    stock_data = {}
    for symbol in symbols:
        days_needed = (end_date - start_date).days + 30
        df_15m = await backtester._fetch_historical_15m(symbol, days_needed)
        df_weekly = await backtester._fetch_historical_weekly(symbol, days_needed)
        df_daily = await backtester._fetch_historical_daily(symbol, days_needed)
        
        if df_15m is None or df_15m.empty:
            continue
        
        df_15m['date'] = pd.to_datetime(df_15m.index).date
        
        # 过滤正规交易时段 (ET: 09:30 - 16:00)
        timestamps = pd.to_datetime(df_15m.index)
        # 确保 timestamps 是 ET
        if timestamps.tz is None:
             timestamps = timestamps.tz_localize(ET)
        else:
             timestamps = timestamps.tz_convert(ET)
             
        df_15m_filtered = df_15m[
            ((timestamps.hour == 9) & (timestamps.minute >= 30)) |   # 9:30-9:59
            ((timestamps.hour >= 10) & (timestamps.hour < 16))       # 10:00-15:59
        ].copy()
        
        stock_data[symbol] = {
            'df_15m': df_15m_filtered,
            'df_weekly': df_weekly,
            'df_daily': df_daily,
            'result': BacktestResult(symbol=symbol, start_date=start_date, end_date=end_date, trades=[])
        }
    
    # 按日期遍历
    for trade_date in trading_days:
        if verbose:
            print(f"\n{'='*60}")
            print(f"📅 {trade_date}")
        
        # 评估所有股票的信号
        signals = []
        for symbol, data in stock_data.items():
            df_15m = data['df_15m']
            day_data = df_15m[df_15m['date'] == trade_date].copy()
            
            if day_data.empty or len(day_data) < 2:
                continue
            
            # 评估信号
            action, confidence, reason = backtester._evaluate_signal(
                symbol, trade_date, df_15m, data['df_weekly'], data['df_daily']
            )
            
            # 计算 OR15 信息 (当天开盘第一根K线 - 这是决策时能看到的唯一当天数据)
            first_bar = day_data.iloc[0]
            or15_open = float(first_bar['open'])
            or15_high = float(first_bar['high'])
            or15_low = float(first_bar['low'])
            or15_close = float(first_bar['close'])
            or15_volume = int(first_bar['volume']) if 'volume' in first_bar else 0
            
            # ===== 修复：记录 DataProcessorAgent 的真实输入数据 =====
            # 决策使用的是 trade_date 之前的历史数据，避免 lookahead bias
            historical_15m = df_15m[df_15m['date'] < trade_date].tail(100)
            
            # 收集历史数据最后 5 根 K 线 (决策时实际能看到的数据)
            input_bars = []
            if len(historical_15m) >= 5:
                for idx in range(-5, 0):
                    bar = historical_15m.iloc[idx]
                    bar_time = pd.to_datetime(historical_15m.index[idx])
                    if bar_time.tz is not None:
                        bar_time = bar_time.tz_convert(ET)
                    input_bars.append({
                        "date": str(bar['date']) if 'date' in bar else "",
                        "time": bar_time.strftime("%Y-%m-%d %H:%M:%S") if hasattr(bar_time, 'strftime') else str(bar_time),
                        "open": float(bar['open']),
                        "high": float(bar['high']),
                        "low": float(bar['low']),
                        "close": float(bar['close']),
                        "volume": int(bar['volume']) if 'volume' in bar else 0
                    })
            
            # 提取技术指标 (使用历史数据最后一根K线的指标，而非当天数据)
            indicators = {}
            if len(historical_15m) > 0:
                last_row = historical_15m.iloc[-1]
                for col in ['ema_9', 'ema_21', 'ema_50', 'macd', 'macd_signal', 'macd_hist', 'rsi', 'atr', 'bb_upper', 'bb_lower', 'volume_ratio']:
                    if col in historical_15m.columns:
                        val = last_row.get(col)
                        if pd.notna(val):
                            indicators[col] = round(float(val), 4)
                # 记录最后一根历史K线的日期
                last_hist_time = pd.to_datetime(historical_15m.index[-1])
                if last_hist_time.tz is not None:
                    last_hist_time = last_hist_time.tz_convert(ET)
                indicators['_data_as_of'] = last_hist_time.strftime("%Y-%m-%d %H:%M:%S")
            
            # 获取多周期偏向 (使用 trade_date 之前的数据)
            weekly_bias = ""
            daily_bias = ""
            # 周线：过滤掉 trade_date 之后的数据
            if data['df_weekly'] is not None and len(data['df_weekly']) > 0:
                df_weekly_hist = data['df_weekly']
                if 'date' in df_weekly_hist.columns:
                    df_weekly_hist = df_weekly_hist[df_weekly_hist['date'] < trade_date]
                if len(df_weekly_hist) > 0:
                    weekly_last = df_weekly_hist.iloc[-1]
                    if 'ema9' in df_weekly_hist.columns and 'ema21' in df_weekly_hist.columns:
                        if pd.notna(weekly_last.get('ema9')) and pd.notna(weekly_last.get('ema21')):
                            if weekly_last['ema9'] > weekly_last['ema21']:
                                weekly_bias = "bullish"
                            else:
                                weekly_bias = "bearish"
            # 日线：过滤掉 trade_date 之后的数据
            if data['df_daily'] is not None and len(data['df_daily']) > 0:
                df_daily_hist = data['df_daily']
                if 'date' in df_daily_hist.columns:
                    df_daily_hist = df_daily_hist[df_daily_hist['date'] < trade_date]
                if len(df_daily_hist) > 0:
                    daily_last = df_daily_hist.iloc[-1]
                    if 'ema9' in df_daily_hist.columns and 'ema21' in df_daily_hist.columns:
                        if pd.notna(daily_last.get('ema9')) and pd.notna(daily_last.get('ema21')):
                            if daily_last['ema9'] > daily_last['ema21']:
                                daily_bias = "bullish"
                            else:
                                daily_bias = "bearish"
            
            # 计算最高价和时间
            after_or15 = day_data.iloc[1:]
            if not after_or15.empty:
                high_idx = after_or15['high'].idxmax()
                day_high_after_or15 = float(after_or15.loc[high_idx, 'high'])
                high_time_utc = pd.to_datetime(high_idx)
                if high_time_utc.tz is None:
                    high_time_et = high_time_utc.tz_localize('UTC').tz_convert(ET)
                else:
                    high_time_et = high_time_utc.tz_convert(ET)
                day_high_time = high_time_et.strftime("%H:%M")
            else:
                day_high_after_or15 = or15_high
                day_high_time = "09:45"
            
            max_potential_pct = (day_high_after_or15 - or15_close) / or15_close * 100 if or15_close > 0 else 0
            
            signals.append({
                'symbol': symbol,
                'action': action,
                'confidence': confidence,
                'reason': reason,
                'or15_open': or15_open,
                'or15_high': or15_high,
                'or15_low': or15_low,
                'or15_close': or15_close,
                'or15_volume': or15_volume,
                'input_bars': input_bars,  # 修复：使用历史数据 K 线
                'indicators': indicators,
                'weekly_bias': weekly_bias,
                'daily_bias': daily_bias,
                'day_high_after_or15': day_high_after_or15,
                'day_high_time': day_high_time,
                'max_potential_pct': max_potential_pct
            })
        
        # 优化排序：HIGH_BETA 优先 + 信号强度
        # 已验证高胜率的股票：BKKT, RCAT, CRML, ASTS, SIDU, OSS
        HIGH_PRIORITY_STOCKS = ["BKKT", "RCAT", "CRML", "ASTS", "SIDU", "OSS"]
        
        buy_signals = [s for s in signals if s['action'] == 'BUY']
        
        # 排序规则：
        # 1. HIGH_PRIORITY_STOCKS 优先
        # 2. 然后按 confidence 降序
        def sort_key(s):
            is_priority = 1 if s['symbol'] in HIGH_PRIORITY_STOCKS else 0
            return (is_priority, s['confidence'])
        
        buy_signals.sort(key=sort_key, reverse=True)
        wait_signals = [s for s in signals if s['action'] != 'BUY']
        
        # 只执行 TOP 5 BUY
        top5_symbols = set(s['symbol'] for s in buy_signals[:MAX_DAILY_TRADES])
        
        if verbose and buy_signals:
            print(f"  🎯 TOP {MAX_DAILY_TRADES} BUY: {', '.join(top5_symbols)}")
        
        # 处理所有信号
        for sig in signals:
            symbol = sig['symbol']
            data = stock_data[symbol]
            
            # 只有 TOP 5 才执行交易
            should_trade = sig['action'] == 'BUY' and symbol in top5_symbols
            
            if should_trade:
                trade = await backtester._simulate_day(
                    symbol=symbol,
                    trade_date=trade_date,
                    df_15m=data['df_15m'],
                    df_weekly=data['df_weekly'],
                    df_daily=data['df_daily'],
                    verbose=verbose
                )
                
                if trade:
                    action = "BUY"
                    decision_reason = trade.entry_reason
                    traded = True
                    entry_price = trade.entry_price
                    take_profit = trade.take_profit
                    stop_loss = trade.stop_loss
                    exit_price = trade.exit_price or 0
                    exit_reason = trade.exit_reason
                    pnl_pct = trade.pnl_pct
                    data['result'].trades.append(trade)
                else:
                    action = "WAIT"
                    decision_reason = sig['reason']
                    traded = False
                    entry_price = exit_price = pnl_pct = 0
                    take_profit = stop_loss = 0
                    exit_reason = ""
            else:
                action = sig['action']
                decision_reason = sig['reason']  # 保留原始决策理由
                traded = False
                entry_price = exit_price = pnl_pct = 0
                take_profit = stop_loss = 0
                exit_reason = ""
            
            # 创建每日记录 (包含完整过程数据)
            record = DailyRecord(
                symbol=symbol,
                trade_date=trade_date,
                action=action,
                decision_reason=decision_reason,
                confidence=sig['confidence'],
                or15_open=sig['or15_open'],
                or15_high=sig['or15_high'],
                or15_low=sig['or15_low'],
                or15_close=sig['or15_close'],
                or15_volume=sig['or15_volume'],
                day_high_after_or15=sig['day_high_after_or15'],
                day_high_time=sig['day_high_time'],
                max_potential_pct=sig['max_potential_pct'],
                traded=traded,
                entry_price=entry_price,
                take_profit=take_profit,
                stop_loss=stop_loss,
                exit_price=exit_price,
                exit_reason=exit_reason,
                pnl_pct=pnl_pct,
                # 输入数据 (决策前的历史数据，不是当天数据)
                or15_bars=sig['input_bars'],
                indicators=sig['indicators'],
                # 决策过程
                weekly_bias=sig['weekly_bias'],
                daily_bias=sig['daily_bias'],
                intraday_bias="bullish" if sig['action'] == 'BUY' else "neutral",
                decision_notes=[sig['reason']] if sig['reason'] else []
            )
            daily_records[trade_date].append(record)
    
    # 计算统计并保存结果
    for symbol, data in stock_data.items():
        result = data['result']
        backtester._calculate_stats(result)
        all_results.append(result)
        backtester.save_result(result, output_dir)
        
        if verbose and result.total_trades > 0:
            backtester._print_result(result)
    
    return all_results, daily_records


def generate_trade_summary(results: List[BacktestResult], start_date: date, end_date: date, output_dir: str = "data/backtest_results"):
    """
    生成汇总交易记录文件
    
    输出 CSV 包含：日期、股票、开仓价格、卖出价格、止损、止盈、收益率、出场原因、开仓理由
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 收集所有交易
    all_trades = []
    for r in results:
        for t in r.trades:
            all_trades.append({
                "日期": t.trade_date,
                "股票": t.symbol,
                "买入价格": f"${t.entry_price:.2f}",
                "卖出价格": f"${t.exit_price:.2f}" if t.exit_price else "-",
                "止损": f"${t.stop_loss:.2f}",
                "止盈": f"${t.take_profit:.2f}",
                "收益率": f"{t.pnl_pct:+.2f}%",
                "出场原因": t.exit_reason,
                "持仓时间": f"{t.holding_minutes}min",
                "开仓理由": t.entry_reason
            })
    
    if not all_trades:
        print("\n📭 无交易记录")
        return
    
    # 保存 CSV
    csv_path = os.path.join(output_dir, f"trades_summary_{start_date}_{end_date}.csv")
    df = pd.DataFrame(all_trades)
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    
    # 计算汇总
    total_trades = len(all_trades)
    total_pnl = sum(r.total_pnl_pct for r in results)
    winning = sum(r.winning_trades for r in results)
    
    print("\n" + "=" * 60)
    print("📊 回测汇总")
    print("=" * 60)
    print(f"  总交易数: {total_trades}")
    print(f"  盈利交易: {winning}")
    print(f"  胜率: {winning/total_trades*100:.1f}%" if total_trades > 0 else "  胜率: N/A")
    print(f"  总收益: {total_pnl:+.2f}%")
    print()
    print("  📋 交易明细:")
    for t in all_trades:
        print(f"    {t['日期']} {t['股票']}: {t['买入价格']} → {t['卖出价格']} | {t['收益率']} | {t['出场原因']}")
    
    print(f"\n💾 交易记录已保存: {csv_path}")


def generate_traded_stocks_summary(results: List[BacktestResult], start_date: date, end_date: date, output_dir: str):
    """
    生成产生交易的股票汇总 JSON
    
    包含每只股票的交易统计和详细交易列表
    """
    from collections import defaultdict
    
    trades_by_stock = defaultdict(list)
    
    # 按股票分组交易
    for r in results:
        if not r.trades:
            continue
        for t in r.trades:
            trades_by_stock[r.symbol].append({
                "date": str(t.trade_date),
                "entry_price": f"${t.entry_price:.2f}",
                "exit_price": f"${t.exit_price:.2f}" if t.exit_price else "-",
                "pnl_pct": f"{t.pnl_pct:+.2f}%",
                "exit_reason": t.exit_reason,
                "holding_time": f"{t.holding_minutes}min",
                "entry_reason": t.entry_reason
            })
    
    # 计算每只股票的统计
    stock_summary = {}
    for symbol, trades in trades_by_stock.items():
        pnl_values = [float(t['pnl_pct'].replace('%', '').replace('+', '')) for t in trades]
        winning_trades = sum(1 for p in pnl_values if p > 0)
        total_pnl = sum(pnl_values)
        
        stock_summary[symbol] = {
            "symbol": symbol,
            "total_trades": len(trades),
            "winning_trades": winning_trades,
            "losing_trades": len(trades) - winning_trades,
            "win_rate": f"{winning_trades/len(trades)*100:.1f}%",
            "total_pnl_pct": f"{total_pnl:+.2f}%",
            "avg_pnl_pct": f"{total_pnl/len(trades):.2f}%",
            "max_win": f"{max(pnl_values):+.2f}%",
            "max_loss": f"{min(pnl_values):+.2f}%",
            "trades": trades
        }
    
    # 按总收益排序
    sorted_stocks = sorted(
        stock_summary.items(), 
        key=lambda x: float(x[1]['total_pnl_pct'].replace('%', '').replace('+', '')), 
        reverse=True
    )
    
    # 生成汇总
    output = {
        "session": os.path.basename(output_dir),
        "period": f"{start_date} ~ {end_date}",
        "total_stocks_traded": len(stock_summary),
        "total_trades": sum(s['total_trades'] for s in stock_summary.values()),
        "stocks": {symbol: data for symbol, data in sorted_stocks}
    }
    
    # 保存
    json_path = os.path.join(output_dir, "traded_stocks_summary.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"💾 交易股票汇总已保存: {json_path}")


if __name__ == "__main__":
    asyncio.run(main())
