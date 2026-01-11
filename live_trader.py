#!/usr/bin/env python3
"""
🚀 Live Trading Service
=======================

实盘模式：
1. 美股开盘时间 (9:30 AM - 4:00 PM ET) 自动运行
2. 开盘后 15 分钟 (9:45 AM) 选出 Top 5 股票并记录入场价
3. 每隔 15 分钟更新收益率
4. 收盘后保存结果到 data/live_results/

Usage:
    python live_trader.py                     # 默认使用所有股票
    python live_trader.py --preset momentum   # 使用高动量股票
    python live_trader.py --test             # 测试模式（不等待市场时间）
"""

import os
import sys
import json
import asyncio
import argparse
from datetime import datetime, date, time, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import pandas as pd
from zoneinfo import ZoneInfo

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.api.alpaca_client import AlpacaClient
from src.config.watchlist_2026 import HIGH_MOMENTUM, AI_RELATED, ALL_TICKERS
from src.agents.simple_agents import DataProcessorAgent, MultiPeriodAgent, DecisionAgent

# 美东时区
ET = ZoneInfo("America/New_York")

# 交易时间配置
MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)
DECISION_TIME = time(9, 45)  # 开盘后 15 分钟决策

# 投资配置
INVESTMENT_PER_STOCK = 10000  # $10,000 per stock
MAX_STOCKS_PER_DAY = 5        # Top 5 stocks per day
DAILY_CAPITAL = INVESTMENT_PER_STOCK * MAX_STOCKS_PER_DAY  # $50,000


@dataclass
class LivePosition:
    """实盘持仓记录"""
    symbol: str
    entry_time: datetime
    entry_price: float
    entry_reason: str
    current_price: float = 0.0
    pnl_pct: float = 0.0
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: str = ""


@dataclass
class LiveSession:
    """实盘交易会话"""
    session_date: date
    positions: List[LivePosition] = field(default_factory=list)
    updates: List[Dict] = field(default_factory=list)  # 每 15 分钟的更新记录
    
    def to_dict(self) -> Dict:
        return {
            "date": str(self.session_date),
            "positions": [
                {
                    "symbol": p.symbol,
                    "entry_time": str(p.entry_time),
                    "entry_price": p.entry_price,
                    "entry_reason": p.entry_reason,
                    "current_price": p.current_price,
                    "pnl_pct": p.pnl_pct,
                    "exit_time": str(p.exit_time) if p.exit_time else None,
                    "exit_price": p.exit_price,
                    "exit_reason": p.exit_reason
                }
                for p in self.positions
            ],
            "updates": self.updates
        }


class LiveTrader:
    """实盘交易器"""
    
    def __init__(self, symbols: List[str]):
        self.symbols = symbols
        self.client = AlpacaClient()
        self.data_agent = DataProcessorAgent()
        self.trend_agent = MultiPeriodAgent()
        self.decision_agent = DecisionAgent()
        
        self.session: Optional[LiveSession] = None
        self.running = True
        
    def is_market_open(self) -> bool:
        """检查市场是否开盘"""
        now = datetime.now(ET)
        current_time = now.time()
        weekday = now.weekday()
        
        # 周末不开盘
        if weekday >= 5:
            return False
        
        # 检查交易时间
        return MARKET_OPEN <= current_time <= MARKET_CLOSE
    
    def is_decision_time(self) -> bool:
        """检查是否到决策时间（9:45 AM）"""
        now = datetime.now(ET)
        current_time = now.time()
        
        # 9:45 时刻进行决策
        return (
            current_time.hour == DECISION_TIME.hour and
            current_time.minute >= DECISION_TIME.minute and
            current_time.minute < DECISION_TIME.minute + 5  # 5 分钟窗口
        )
    
    def get_next_15min_mark(self) -> datetime:
        """获取下一个 15 分钟整点"""
        now = datetime.now(ET)
        minutes = now.minute
        next_quarter = ((minutes // 15) + 1) * 15
        
        if next_quarter >= 60:
            next_time = now.replace(hour=now.hour + 1, minute=0, second=0, microsecond=0)
        else:
            next_time = now.replace(minute=next_quarter, second=0, microsecond=0)
        
        return next_time
    
    async def fetch_stock_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """获取股票 15 分钟 K 线数据"""
        try:
            bars = self.client.get_bars(symbol, '15m', limit=100)
            if bars:
                return self.client.to_dataframe(bars)
            return None
        except Exception as e:
            print(f"  ⚠️ 获取 {symbol} 数据失败: {e}")
            return None
    
    async def evaluate_all_stocks(self) -> List[Tuple[str, float, str, float]]:
        """
        评估所有股票，返回 (symbol, confidence, reason, current_price) 列表
        """
        signals = []
        
        print(f"\n📊 评估 {len(self.symbols)} 只股票...")
        
        for symbol in self.symbols:
            try:
                df = await self.fetch_stock_data(symbol)
                if df is None or len(df) < 10:
                    continue
                
                # 获取最新价格
                current_price = float(df.iloc[-1]['close'])
                
                # 简化的信号评估
                # 使用最近 5 根 K 线的趋势
                recent = df.tail(5)
                price_change = (recent.iloc[-1]['close'] - recent.iloc[0]['open']) / recent.iloc[0]['open']
                volume_avg = recent['volume'].mean()
                
                # 计算动量分数
                if price_change > 0.01 and volume_avg > 100000:
                    confidence = min(price_change * 100, 10)  # 0-10 分
                    reason = f"动量突破 +{price_change*100:.1f}%"
                    signals.append((symbol, confidence, reason, current_price))
                    print(f"  ✅ {symbol}: {reason} @ ${current_price:.2f}")
                
            except Exception as e:
                print(f"  ⚠️ {symbol} 评估失败: {e}")
                continue
        
        # 按 confidence 排序，取 Top 5
        signals.sort(key=lambda x: x[1], reverse=True)
        return signals[:MAX_STOCKS_PER_DAY]
    
    async def open_positions(self, signals: List[Tuple[str, float, str, float]]):
        """开仓建立头寸"""
        if not signals:
            print("  ⚠️ 无有效信号，今日不交易")
            return
        
        self.session = LiveSession(session_date=date.today())
        
        print(f"\n🎯 开仓 Top {len(signals)} 只股票:")
        
        for symbol, confidence, reason, entry_price in signals:
            position = LivePosition(
                symbol=symbol,
                entry_time=datetime.now(ET),
                entry_price=entry_price,
                entry_reason=reason,
                current_price=entry_price,
                pnl_pct=0.0
            )
            self.session.positions.append(position)
            print(f"  💰 {symbol}: ${entry_price:.2f} | {reason}")
        
        # 保存初始状态
        self._save_session()
    
    async def update_positions(self):
        """更新持仓收益"""
        if not self.session or not self.session.positions:
            return
        
        now = datetime.now(ET)
        update_record = {
            "time": str(now),
            "positions": []
        }
        
        print(f"\n🔄 更新持仓 @ {now.strftime('%H:%M')}")
        
        total_pnl_usd = 0
        
        for pos in self.session.positions:
            try:
                # 获取最新价格
                df = await self.fetch_stock_data(pos.symbol)
                if df is not None and len(df) > 0:
                    pos.current_price = float(df.iloc[-1]['close'])
                    pos.pnl_pct = (pos.current_price - pos.entry_price) / pos.entry_price * 100
                    
                    pnl_usd = INVESTMENT_PER_STOCK * (pos.pnl_pct / 100)
                    total_pnl_usd += pnl_usd
                    
                    emoji = "📈" if pos.pnl_pct >= 0 else "📉"
                    print(f"  {emoji} {pos.symbol}: ${pos.current_price:.2f} ({pos.pnl_pct:+.2f}%) ${pnl_usd:+.0f}")
                    
                    update_record["positions"].append({
                        "symbol": pos.symbol,
                        "price": pos.current_price,
                        "pnl_pct": pos.pnl_pct
                    })
            except Exception as e:
                print(f"  ⚠️ {pos.symbol} 更新失败: {e}")
        
        # 计算总收益
        total_pnl_pct = total_pnl_usd / DAILY_CAPITAL * 100
        update_record["total_pnl_pct"] = total_pnl_pct
        update_record["total_pnl_usd"] = total_pnl_usd
        
        self.session.updates.append(update_record)
        
        print(f"\n  💰 总收益: ${total_pnl_usd:+.0f} ({total_pnl_pct:+.2f}%)")
        
        # 保存更新
        self._save_session()
    
    async def close_positions(self):
        """收盘平仓"""
        if not self.session or not self.session.positions:
            return
        
        print(f"\n🔔 收盘平仓")
        
        total_pnl_usd = 0
        
        for pos in self.session.positions:
            try:
                df = await self.fetch_stock_data(pos.symbol)
                if df is not None and len(df) > 0:
                    pos.exit_time = datetime.now(ET)
                    pos.exit_price = float(df.iloc[-1]['close'])
                    pos.exit_reason = "MARKET_CLOSE"
                    pos.pnl_pct = (pos.exit_price - pos.entry_price) / pos.entry_price * 100
                    
                    pnl_usd = INVESTMENT_PER_STOCK * (pos.pnl_pct / 100)
                    total_pnl_usd += pnl_usd
                    
                    emoji = "✅" if pos.pnl_pct >= 0 else "❌"
                    print(f"  {emoji} {pos.symbol}: ${pos.entry_price:.2f} → ${pos.exit_price:.2f} ({pos.pnl_pct:+.2f}%)")
            except Exception as e:
                print(f"  ⚠️ {pos.symbol} 平仓失败: {e}")
        
        total_pnl_pct = total_pnl_usd / DAILY_CAPITAL * 100
        print(f"\n  📊 今日总结: ${total_pnl_usd:+.0f} ({total_pnl_pct:+.2f}%)")
        
        self._save_session()
        self._save_daily_summary()
    
    def _save_session(self):
        """保存会话状态"""
        if not self.session:
            return
        
        # 创建目录
        today_str = str(self.session.session_date)
        output_dir = f"data/live_results/{today_str}"
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存 session.json
        session_path = f"{output_dir}/session.json"
        with open(session_path, 'w', encoding='utf-8') as f:
            json.dump(self.session.to_dict(), f, indent=2, ensure_ascii=False)
    
    def _save_daily_summary(self):
        """保存每日汇总 CSV（与回测格式一致）"""
        if not self.session:
            return
        
        today_str = str(self.session.session_date)
        output_dir = "data/live_results"
        os.makedirs(output_dir, exist_ok=True)
        
        # 准备数据
        records = []
        for pos in self.session.positions:
            pnl_str = f"{pos.pnl_pct:+.2f}%" if pos.exit_price else "-"
            records.append({
                "日期": today_str,
                "股票": pos.symbol,
                "决策": "BUY",
                "决策理由": pos.entry_reason,
                "OR15收盘价": f"${pos.entry_price:.2f}",
                "开仓价格": f"${pos.entry_price:.2f}",
                "卖出价格": f"${pos.exit_price:.2f}" if pos.exit_price else "-",
                "收益率": pnl_str,
                "出场原因": pos.exit_reason or "-",
                "当日最高价": "-",
                "最高价时间": "-",
                "最大潜在收益": "-",
                "是否交易": "是"
            })
        
        # 追加到 daily_summary.csv
        csv_path = f"{output_dir}/daily_summary.csv"
        df = pd.DataFrame(records)
        
        # 如果文件已存在，追加；否则创建
        if os.path.exists(csv_path):
            existing = pd.read_csv(csv_path, encoding='utf-8-sig')
            # 删除今天的旧记录
            existing = existing[existing['日期'] != today_str]
            df = pd.concat([existing, df], ignore_index=True)
        
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"\n💾 已保存: {csv_path}")
        
        # 同时保存 trades_summary.csv（与回测格式一致）
        trades_path = f"{output_dir}/trades_summary.csv"
        trades_records = []
        for pos in self.session.positions:
            if pos.exit_price:
                trades_records.append({
                    "日期": today_str,
                    "股票": pos.symbol,
                    "买入价格": f"${pos.entry_price:.2f}",
                    "卖出价格": f"${pos.exit_price:.2f}",
                    "收益率": f"{pos.pnl_pct:+.2f}%",
                    "出场原因": pos.exit_reason,
                    "持仓时间": "-",
                    "开仓理由": pos.entry_reason
                })
        
        if trades_records:
            trades_df = pd.DataFrame(trades_records)
            if os.path.exists(trades_path):
                existing = pd.read_csv(trades_path, encoding='utf-8-sig')
                existing = existing[existing['日期'] != today_str]
                trades_df = pd.concat([existing, trades_df], ignore_index=True)
            trades_df.to_csv(trades_path, index=False, encoding='utf-8-sig')
            print(f"💾 已保存: {trades_path}")
    
    async def run(self, test_mode: bool = False):
        """主运行循环"""
        print("=" * 60)
        print("🚀 Live Trading Service 启动")
        print("=" * 60)
        print(f"  股票池: {len(self.symbols)} 只")
        print(f"  每只投入: ${INVESTMENT_PER_STOCK:,}")
        print(f"  总投入: ${DAILY_CAPITAL:,}")
        print(f"  本地时间: {datetime.now()}")
        print(f"  美东时间: {datetime.now(ET)}")
        print()
        
        positions_opened = False
        
        while self.running:
            now = datetime.now(ET)
            
            if test_mode:
                # 测试模式：立即执行
                print("⚠️ 测试模式 - 立即执行")
                signals = await self.evaluate_all_stocks()
                if signals:
                    await self.open_positions(signals)
                    await asyncio.sleep(5)
                    await self.update_positions()
                    await asyncio.sleep(5)
                    await self.close_positions()
                print("\n✅ 测试完成")
                break
            
            # 检查市场状态
            if not self.is_market_open():
                next_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
                if now.time() > MARKET_CLOSE:
                    next_open += timedelta(days=1)
                
                wait_seconds = (next_open - now).total_seconds()
                if wait_seconds > 0:
                    print(f"⏳ 等待开盘... 下一开盘: {next_open.strftime('%Y-%m-%d %H:%M')} ET")
                    await asyncio.sleep(min(wait_seconds, 300))  # 最多等 5 分钟再检查
                continue
            
            # 开盘时段
            if self.is_decision_time() and not positions_opened:
                # 9:45 AM - 选股开仓
                print(f"\n🔔 决策时间到！{now.strftime('%H:%M')} ET")
                signals = await self.evaluate_all_stocks()
                await self.open_positions(signals)
                positions_opened = True
                
            elif positions_opened and now.minute % 15 == 0:
                # 每 15 分钟更新
                await self.update_positions()
            
            # 检查收盘
            if now.time() >= MARKET_CLOSE:
                await self.close_positions()
                print("\n✅ 今日交易结束，等待明日...")
                positions_opened = False
                # 等待到明天
                await asyncio.sleep(3600)  # 等 1 小时
                continue
            
            # 等待下一个检查点
            next_mark = self.get_next_15min_mark()
            wait_seconds = (next_mark - now).total_seconds()
            if wait_seconds > 0:
                print(f"\n⏳ 下次更新: {next_mark.strftime('%H:%M')} ET (等待 {int(wait_seconds)}s)")
                await asyncio.sleep(wait_seconds)


async def main():
    parser = argparse.ArgumentParser(description="Live Trading Service")
    parser.add_argument("--symbols", type=str, help="股票代码，逗号分隔")
    parser.add_argument("--preset", type=str, choices=["momentum", "ai", "all"], 
                        default="momentum", help="预设股票池")
    parser.add_argument("--test", action="store_true", help="测试模式（不等待市场时间）")
    
    args = parser.parse_args()
    
    # 选择股票
    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",")]
    else:
        if args.preset == "momentum":
            symbols = HIGH_MOMENTUM
        elif args.preset == "ai":
            symbols = AI_RELATED[:10]
        else:
            symbols = ALL_TICKERS
    
    # 启动交易器
    trader = LiveTrader(symbols)
    
    try:
        await trader.run(test_mode=args.test)
    except KeyboardInterrupt:
        print("\n\n👋 用户中断，正在保存...")
        if trader.session:
            await trader.close_positions()
        print("✅ 已安全退出")


if __name__ == "__main__":
    asyncio.run(main())
