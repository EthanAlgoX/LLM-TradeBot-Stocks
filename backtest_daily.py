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
from typing import List, Dict, Optional, Tuple
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

# 美东时区
ET = ZoneInfo("America/New_York")

# 交易时间
MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)
STRATEGY_TIME = time(9, 45)  # 开盘后 15 分钟


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
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "trade_date": str(self.trade_date),
            "entry_time": self.entry_time.isoformat() if self.entry_time else None,
            "entry_price": self.entry_price,
            "entry_reason": self.entry_reason,
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "exit_price": self.exit_price,
            "exit_reason": self.exit_reason,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "pnl": self.pnl,
            "pnl_pct": self.pnl_pct,
            "holding_minutes": self.holding_minutes
        }


@dataclass
class DailyRecord:
    """每日每股票记录 (包括未开仓)"""
    symbol: str
    trade_date: date
    
    # 决策信息
    action: str  # BUY / WAIT / REJECT
    decision_reason: str
    
    # OR15 信息
    or15_high: float = 0.0
    or15_low: float = 0.0
    or15_close: float = 0.0  # 第一根K线收盘价
    
    # 最大潜在收益 (当日OR15后最高价 - OR15 close)
    day_high_after_or15: float = 0.0
    max_potential_pct: float = 0.0  # (day_high - or15_close) / or15_close * 100
    
    # 实际交易信息 (如果开仓)
    traded: bool = False
    entry_price: float = 0.0
    exit_price: float = 0.0
    exit_reason: str = ""
    pnl_pct: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "trade_date": str(self.trade_date),
            "action": self.action,
            "decision_reason": self.decision_reason,
            "or15_high": self.or15_high,
            "or15_low": self.or15_low,
            "or15_close": self.or15_close,
            "day_high_after_or15": self.day_high_after_or15,
            "max_potential_pct": self.max_potential_pct,
            "traded": self.traded,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "exit_reason": self.exit_reason,
            "pnl_pct": self.pnl_pct
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
        """获取历史 15 分钟数据"""
        try:
            bars = self.cache.get_bars(symbol, '15m', days=days)
            if bars:
                df = self.cache.to_dataframe(bars)
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
        # 美股正常交易时间: 9:30 AM - 4:00 PM ET = 14:30 - 21:00 UTC
        timestamps = pd.to_datetime(day_data.index)
        day_data = day_data[
            ((timestamps.hour == 14) & (timestamps.minute >= 30)) |  # 14:30-14:59 UTC
            ((timestamps.hour >= 15) & (timestamps.hour < 21))       # 15:00-20:59 UTC
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
        
        # 创建 ProcessedData (模拟当时的数据环境)
        # 关键: 9:45 AM 时只能看到:
        # - 历史 15 分钟数据 (用于计算均量)
        # - 今天的前两根 K 线 (OR15 + 确认)
        # 不能看到当天后续的数据，避免 look-ahead bias
        
        # 获取历史 15 分钟数据 (当天之前)
        historical_15m = df_15m[df_15m['date'] < trade_date].copy()
        
        # 今天的前两根 K 线
        today_bars = day_data.iloc[:2]
        
        # 合并: 历史数据 + 今天前两根
        bars_for_decision = pd.concat([historical_15m, today_bars])
        
        # 入场价 = 第二根 K 线收盘价
        entry_price = float(today_bars.iloc[-1]['close'])
        
        processed = ProcessedData(
            symbol=symbol,
            df_weekly=df_weekly[df_weekly.index.date < trade_date] if df_weekly is not None else None,
            df_daily=df_daily[df_daily.index.date < trade_date] if df_daily is not None else None,
            df_15m=bars_for_decision,  # 历史数据 + 今天前两根
            current_price=entry_price,
            timestamp=datetime.combine(trade_date, STRATEGY_TIME, tzinfo=ET)
        )
        
        # 趋势分析
        trend = self.trend_agent.analyze(processed)
        
        # 决策
        decision = self.decision_agent.decide(processed, trend)
        
        if verbose:
            print(f"\n  📅 {trade_date} | {decision.action} | {decision.summary_reason}")
        
        # 只有 BUY 才模拟持仓
        if decision.action != 'BUY':
            return None
        
        # 创建交易记录
        entry_time = datetime.combine(trade_date, STRATEGY_TIME, tzinfo=ET)
        trade = BacktestTrade(
            symbol=symbol,
            trade_date=trade_date,
            entry_time=entry_time,
            entry_price=decision.entry_price,
            entry_reason=decision.summary_reason,
            stop_loss=decision.stop_loss,
            take_profit=decision.take_profit
        )
        
        if verbose:
            print(f"     💰 买入 ${trade.entry_price:.2f} | 止损 ${trade.stop_loss:.2f} | 止盈 ${trade.take_profit:.2f}")
        
        # 模拟后续 K 线，判断是否触发止损/止盈
        # 注意: 入场是在 9:45，即第一根 K 线收盘后
        # 所以需要从第二根 K 线 (index=1) 开始检查止损/止盈
        for i in range(1, len(day_data)):
            bar = day_data.iloc[i]
            bar_time = pd.to_datetime(bar.name)
            bar_high = float(bar['high'])
            bar_low = float(bar['low'])
            bar_close = float(bar['close'])
            
            # 检查止盈 (优先判断止盈)
            if bar_high >= trade.take_profit:
                trade.exit_time = bar_time
                trade.exit_price = trade.take_profit
                trade.exit_reason = "TAKE_PROFIT"
                break
            
            # 检查止损
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
        
        # 计算盈亏
        trade.pnl = trade.exit_price - trade.entry_price
        trade.pnl_pct = (trade.pnl / trade.entry_price) * 100
        
        # 计算持仓时间 (基于 K 线数量，每根 15 分钟)
        # 找到入场后的第一根 K 线和出场 K 线的索引差
        exit_bar_time = trade.exit_time
        entry_bar_time = pd.to_datetime(day_data.iloc[0].name)  # OR15 bar
        
        # 简化计算: 从入场 (9:45) 到出场的分钟数
        # 将两个时间都转换为 minutes since midnight ET
        exit_minutes = (exit_bar_time.hour * 60 + exit_bar_time.minute) + 15  # bar 结束时间
        entry_minutes = 9 * 60 + 45  # 9:45 AM ET
        trade.holding_minutes = exit_minutes - entry_minutes
        
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


async def main():
    parser = argparse.ArgumentParser(description="美股日内回测系统")
    parser.add_argument("--symbols", type=str, default="AAPL", help="股票代码，逗号分隔")
    parser.add_argument("--days", type=int, default=30, help="回测天数")
    parser.add_argument("--html", action="store_true", help="生成 HTML 报告")
    parser.add_argument("--quiet", action="store_true", help="安静模式")
    
    args = parser.parse_args()
    
    symbols = [s.strip().upper() for s in args.symbols.split(",")]
    end_date = date.today()
    start_date = end_date - timedelta(days=args.days)
    
    # 创建本次回测的输出目录 (按运行时间命名)
    run_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = f"data/backtest_results/{run_timestamp}"
    os.makedirs(output_dir, exist_ok=True)
    
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


def save_daily_records(daily_records: Dict[date, List[DailyRecord]], output_dir: str):
    """
    保存每日每股票记录到子文件夹
    
    结构:
    output_dir/
      2026-01-05/
        AAPL.json
        GOOGL.json
        ...
      2026-01-06/
        ...
    """
    for trade_date, records in daily_records.items():
        # 创建日期子文件夹
        date_dir = os.path.join(output_dir, str(trade_date))
        os.makedirs(date_dir, exist_ok=True)
        
        for record in records:
            # 保存每只股票的记录
            filepath = os.path.join(date_dir, f"{record.symbol}.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(record.to_dict(), f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 每日记录已保存: {output_dir}/[日期]/[股票].json")


async def run_backtest_all(
    symbols: List[str],
    start_date: date,
    end_date: date,
    output_dir: str,
    verbose: bool = True
) -> Tuple[List[BacktestResult], Dict[date, List[DailyRecord]]]:
    """
    运行多股票回测，返回回测结果和每日记录
    """
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
    
    for symbol in symbols:
        # 获取历史数据
        days_needed = (end_date - start_date).days + 30
        df_15m = await backtester._fetch_historical_15m(symbol, days_needed)
        df_weekly = await backtester._fetch_historical_weekly(symbol, days_needed)
        df_daily = await backtester._fetch_historical_daily(symbol, days_needed)
        
        if df_15m is None or df_15m.empty:
            continue
        
        df_15m['date'] = pd.to_datetime(df_15m.index).date
        
        result = BacktestResult(symbol=symbol, start_date=start_date, end_date=end_date, trades=[])
        
        # 过滤正规交易时段
        timestamps = pd.to_datetime(df_15m.index)
        df_15m_filtered = df_15m[
            ((timestamps.hour == 14) & (timestamps.minute >= 30)) |
            ((timestamps.hour >= 15) & (timestamps.hour < 21))
        ].copy()
        
        for trade_date in trading_days:
            # 获取当天数据
            day_data = df_15m_filtered[df_15m_filtered['date'] == trade_date].copy()
            
            if day_data.empty or len(day_data) < 2:
                continue
            
            # 计算 OR15 信息
            first_bar = day_data.iloc[0]
            or15_high = float(first_bar['high'])
            or15_low = float(first_bar['low'])
            or15_close = float(first_bar['close'])
            
            # 计算当日 OR15 后最高价
            remaining_bars = day_data.iloc[1:]  # OR15 之后的 K 线
            if len(remaining_bars) > 0:
                day_high_after_or15 = float(remaining_bars['high'].max())
            else:
                day_high_after_or15 = or15_high
            
            # 最大潜在收益
            max_potential_pct = (day_high_after_or15 - or15_close) / or15_close * 100 if or15_close > 0 else 0
            
            # 模拟交易
            trade = await backtester._simulate_day(
                symbol=symbol,
                trade_date=trade_date,
                df_15m=df_15m_filtered,
                df_weekly=df_weekly,
                df_daily=df_daily,
                verbose=verbose
            )
            
            # 获取决策信息 (通过重新调用 decide 或从 trade 中推断)
            if trade:
                action = "BUY"
                decision_reason = trade.entry_reason
                traded = True
                entry_price = trade.entry_price
                exit_price = trade.exit_price or 0
                exit_reason = trade.exit_reason
                pnl_pct = trade.pnl_pct
                result.trades.append(trade)
            else:
                action = "WAIT"
                decision_reason = "未满足入场条件"
                traded = False
                entry_price = 0
                exit_price = 0
                exit_reason = ""
                pnl_pct = 0
            
            # 创建每日记录
            record = DailyRecord(
                symbol=symbol,
                trade_date=trade_date,
                action=action,
                decision_reason=decision_reason,
                or15_high=or15_high,
                or15_low=or15_low,
                or15_close=or15_close,
                day_high_after_or15=day_high_after_or15,
                max_potential_pct=max_potential_pct,
                traded=traded,
                entry_price=entry_price,
                exit_price=exit_price,
                exit_reason=exit_reason,
                pnl_pct=pnl_pct
            )
            daily_records[trade_date].append(record)
        
        # 计算统计
        backtester._calculate_stats(result)
        all_results.append(result)
        
        # 保存结果
        backtester.save_result(result, output_dir)
        
        if verbose:
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


if __name__ == "__main__":
    asyncio.run(main())
