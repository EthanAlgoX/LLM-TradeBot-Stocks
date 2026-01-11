#!/usr/bin/env python3
"""
🤖 Daily Stock Trader - 每日定时交易系统
========================================

简化版交易入口，特点：
1. 只在开盘后 15 分钟运行 (9:45 AM ET)
2. 每天只运行一次
3. 使用三个核心 Agent：数据处理 → 多周期分析 → 决策输出

Usage:
    # 正常模式：等待 9:45 AM ET 自动执行
    python daily_trader.py
    
    # 测试模式：立即执行一次
    python daily_trader.py --test
    
    # 指定股票
    python daily_trader.py --symbols AAPL,TSLA,NVDA

Author: AI Trader Team
Date: 2026-01-11
"""

import asyncio
import argparse
from datetime import datetime, time
from typing import List, Dict, Optional
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# 版本
from src.version import VERSION

# 美东时区
ET = ZoneInfo("America/New_York")

# 交易时间配置
TRADING_TIME = time(9, 45)  # 开盘后 15 分钟
MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)


class DailyScheduler:
    """
    每日定时调度器
    
    只在美东时间 9:45 AM 执行一次交易策略
    """
    
    def __init__(self):
        self._executed_today = False
        self._last_execution_date = None
    
    def is_trading_time(self) -> bool:
        """检查是否到达交易时间"""
        now_et = datetime.now(ET)
        current_time = now_et.time()
        current_date = now_et.date()
        
        # 重置每日执行标记
        if self._last_execution_date != current_date:
            self._executed_today = False
            self._last_execution_date = current_date
        
        # 已执行过则跳过
        if self._executed_today:
            return False
        
        # 检查是否为交易日（周一到周五）
        if now_et.weekday() >= 5:  # 周六=5, 周日=6
            return False
        
        # 检查是否在交易时间 (9:45 - 9:50)
        if TRADING_TIME <= current_time < time(9, 50):
            return True
        
        return False
    
    def mark_executed(self):
        """标记今日已执行"""
        self._executed_today = True
        self._last_execution_date = datetime.now(ET).date()
    
    def get_status(self) -> str:
        """获取当前状态"""
        now_et = datetime.now(ET)
        current_time = now_et.time()
        
        if self._executed_today:
            return f"✅ 今日已执行 ({self._last_execution_date})"
        
        if now_et.weekday() >= 5:
            return f"📅 非交易日 (周末)"
        
        if current_time < MARKET_OPEN:
            return f"⏰ 等待开盘 (开盘时间: 9:30 AM ET)"
        
        if current_time < TRADING_TIME:
            mins_left = (TRADING_TIME.hour * 60 + TRADING_TIME.minute) - \
                       (current_time.hour * 60 + current_time.minute)
            return f"⏳ 等待交易时间 (还剩 {mins_left} 分钟)"
        
        if current_time >= MARKET_CLOSE:
            return f"🔒 市场已收盘"
        
        return f"🎯 交易时间 ({TRADING_TIME.strftime('%H:%M')} AM ET)"
    
    def seconds_until_trading_time(self) -> int:
        """计算距离下次交易时间的秒数"""
        now_et = datetime.now(ET)
        
        # 计算今天的交易时间
        trading_datetime = datetime.combine(now_et.date(), TRADING_TIME, tzinfo=ET)
        
        if now_et >= trading_datetime:
            # 已过交易时间，计算到明天
            from datetime import timedelta
            trading_datetime += timedelta(days=1)
            
            # 跳过周末
            while trading_datetime.weekday() >= 5:
                trading_datetime += timedelta(days=1)
        
        delta = trading_datetime - now_et
        return int(delta.total_seconds())


class DailyTrader:
    """
    每日交易执行器
    
    使用简化的三 Agent 工作流：
    1. DataProcessorAgent - 数据处理
    2. MultiPeriodAgent - 多周期分析
    3. DecisionAgent - 决策输出
    """
    
    def __init__(
        self,
        symbols: Optional[List[str]] = None,
        paper: bool = True,
        max_position_size: float = 1000.0
    ):
        """
        初始化每日交易器
        
        Args:
            symbols: 股票代码列表 (默认使用内置列表)
            paper: True=模拟盘, False=实盘
            max_position_size: 单笔最大仓位 (USD)
        """
        print("\n" + "=" * 60)
        print(f"🤖 Daily Stock Trader ({VERSION})")
        print("=" * 60)
        
        self.paper = paper
        self.max_position_size = max_position_size
        
        # 默认股票列表
        self.symbols = symbols or ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA", "META", "AMD"]
        
        # 初始化组件
        print("\n🚀 初始化组件...")
        
        from src.agents.simple_agents import DataProcessorAgent, MultiPeriodAgent, DecisionAgent
        from src.api.alpaca_trader import AlpacaTrader
        
        self.data_agent = DataProcessorAgent()
        self.trend_agent = MultiPeriodAgent()
        self.decision_agent = DecisionAgent()
        self.trader = AlpacaTrader(paper=paper)
        self.scheduler = DailyScheduler()
        
        print(f"  ✅ DataProcessorAgent ready")
        print(f"  ✅ MultiPeriodAgent ready")
        print(f"  ✅ DecisionAgent ready")
        print(f"  ✅ AlpacaTrader ready ({'PAPER' if paper else '🔴 LIVE'})")
        
        print(f"\n⚙️  配置:")
        print(f"  - 股票: {', '.join(self.symbols)}")
        print(f"  - 交易时间: 9:45 AM ET")
        print(f"  - 最大仓位: ${max_position_size:.2f}")
        print(f"  - 模式: {'模拟盘' if paper else '🔴 实盘'}")
    
    async def run_once(self) -> Dict[str, Dict]:
        """
        运行一次完整交易流程
        
        Returns:
            Dict: {symbol: decision_dict, ...}
        """
        # 初始化日志记录器
        from src.utils.agent_logger import (
            AgentDataLogger, dataframe_to_summary, 
            trend_analysis_to_dict, or15_signal_to_dict, decision_to_dict
        )
        logger = AgentDataLogger()
        
        print("\n" + "=" * 60)
        now_et = datetime.now(ET)
        print(f"🎯 执行交易策略 | {now_et.strftime('%Y-%m-%d %H:%M:%S')} ET")
        print("=" * 60)
        
        results = {}
        buy_decisions = []
        
        for symbol in self.symbols:
            try:
                print(f"\n{'─'*50}")
                print(f"📊 处理 {symbol}")
                print(f"{'─'*50}")
                
                # Step 1: 数据处理
                data = await self.data_agent.process(symbol)
                
                # 记录数据处理结果
                logger.log_data_processor(
                    symbol,
                    raw_data_info={
                        "weekly_bars": len(data.df_weekly) if data.df_weekly is not None else 0,
                        "daily_bars": len(data.df_daily) if data.df_daily is not None else 0,
                        "15m_bars": len(data.df_15m) if data.df_15m is not None else 0,
                        "current_price": data.current_price,
                        "timestamp": data.timestamp.isoformat()
                    },
                    indicators={
                        "weekly": dataframe_to_summary(data.df_weekly, "weekly"),
                        "daily": dataframe_to_summary(data.df_daily, "daily"),
                        "15m": dataframe_to_summary(data.df_15m, "15m")
                    }
                )
                
                # Step 2: 多周期分析
                trend = self.trend_agent.analyze(data)
                
                # 记录趋势分析结果
                logger.log_multi_period(
                    symbol,
                    weekly_analysis={
                        "bias": trend.weekly_bias.value,
                        "score": trend.weekly_score
                    },
                    daily_analysis={
                        "bias": trend.daily_bias.value,
                        "score": trend.daily_score
                    },
                    combined={
                        "total_score": trend.total_score,
                        "reasons": trend.reasons
                    }
                )
                
                # Step 3: 决策输出
                decision = self.decision_agent.decide(data, trend)
                
                # 记录决策结果
                logger.log_decision(
                    symbol,
                    or15_analysis=or15_signal_to_dict(decision.or15_signal),
                    final_decision=decision_to_dict(decision)
                )
                
                # 保存日志到文件
                logger.save(symbol)
                
                results[symbol] = decision.to_dict()
                
                # 收集买入信号
                if decision.action == 'BUY':
                    buy_decisions.append(decision)
                
            except Exception as e:
                print(f"  ❌ 处理 {symbol} 失败: {e}")
                results[symbol] = {'action': 'ERROR', 'error': str(e)}
        
        # 执行买入
        if buy_decisions:
            print("\n" + "=" * 60)
            print(f"💰 执行买入订单 ({len(buy_decisions)} 个)")
            print("=" * 60)
            
            for decision in buy_decisions:
                await self._execute_buy(decision)
        else:
            print("\n📊 今日无买入信号")
        
        # 打印汇总
        self._print_summary(results)
        
        print(f"\n📁 日志已保存到: data/agent_logs/{datetime.now().strftime('%Y-%m-%d')}/")
        
        return results
    
    async def _execute_buy(self, decision):
        """执行买入订单"""
        try:
            symbol = decision.symbol
            entry_price = decision.entry_price
            stop_loss = decision.stop_loss
            take_profit = decision.take_profit
            
            # 计算股数
            shares = int(self.max_position_size / entry_price)
            if shares <= 0:
                print(f"  ⚠️ {symbol}: 价格过高，无法买入")
                return
            
            print(f"\n  🔔 买入 {symbol}:")
            print(f"     股数: {shares}")
            print(f"     入场: ${entry_price:.2f}")
            print(f"     止损: ${stop_loss:.2f}")
            print(f"     止盈: ${take_profit:.2f}")
            
            # 下单
            order = await self.trader.open_long(
                symbol, shares,
                stop_loss_price=stop_loss,
                take_profit_price=take_profit
            )
            
            if order:
                print(f"     ✅ 订单已提交: {order.id[:8]}...")
            else:
                print(f"     ⚠️ 订单提交失败")
                
        except Exception as e:
            print(f"  ❌ 执行买入失败: {e}")
    
    def _print_summary(self, results: Dict):
        """打印汇总信息"""
        print("\n" + "=" * 60)
        print("📋 决策汇总")
        print("=" * 60)
        
        buy_count = 0
        wait_count = 0
        reject_count = 0
        
        for symbol, result in results.items():
            action = result.get('action', 'UNKNOWN')
            score = result.get('total_score', 0)
            
            if action == 'BUY':
                buy_count += 1
                icon = '🟢'
            elif action == 'WAIT':
                wait_count += 1
                icon = '🟡'
            else:
                reject_count += 1
                icon = '🔴'
            
            print(f"  {icon} {symbol}: {action} (得分: {score})")
        
        print(f"\n  统计: 买入 {buy_count} | 等待 {wait_count} | 拒绝 {reject_count}")
    
    async def run_scheduled(self):
        """
        按计划运行交易策略
        
        每天 9:45 AM ET 执行一次
        """
        print("\n🕐 进入定时模式...")
        print(f"   交易时间: {TRADING_TIME.strftime('%H:%M')} AM ET")
        print("   按 Ctrl+C 停止\n")
        
        try:
            while True:
                # 显示状态
                status = self.scheduler.get_status()
                now_et = datetime.now(ET).strftime('%H:%M:%S')
                print(f"\r⏰ {now_et} ET | {status}    ", end="", flush=True)
                
                if self.scheduler.is_trading_time():
                    print()  # 换行
                    await self.run_once()
                    self.scheduler.mark_executed()
                    print("\n✅ 今日交易已完成，等待明天...")
                
                # 每 30 秒检查一次
                await asyncio.sleep(30)
                
        except KeyboardInterrupt:
            print("\n\n⛔ 已停止")
    
    async def cleanup(self):
        """清理资源"""
        await self.trader.close()


async def main():
    parser = argparse.ArgumentParser(description="Daily Stock Trader (每日定时交易)")
    parser.add_argument("--test", action="store_true", help="测试模式：立即执行一次")
    parser.add_argument("--symbols", type=str, help="股票代码，逗号分隔 (例: AAPL,TSLA)")
    parser.add_argument("--paper", action="store_true", default=True, help="模拟盘 (默认)")
    parser.add_argument("--live", action="store_true", help="实盘 (危险!)")
    parser.add_argument("--position-size", type=float, default=1000.0, help="单笔最大仓位 (USD)")
    
    args = parser.parse_args()
    
    # 解析股票列表
    symbols = None
    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",")]
    
    # 确定模式
    paper = not args.live
    
    if not paper:
        print("\n⚠️  警告: 实盘模式!")
        print("   真金白银，风险自负。确定继续? (y/N)")
        confirm = input().strip().lower()
        if confirm != 'y':
            print("已取消")
            return
    
    # 创建交易器
    trader = DailyTrader(
        symbols=symbols,
        paper=paper,
        max_position_size=args.position_size
    )
    
    try:
        if args.test:
            # 测试模式：立即执行一次
            print("\n🧪 测试模式：立即执行")
            await trader.run_once()
        else:
            # 正常模式：按计划运行
            await trader.run_scheduled()
    finally:
        await trader.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
