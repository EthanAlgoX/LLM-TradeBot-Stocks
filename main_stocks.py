#!/usr/bin/env python3
"""
🤖 LLM-TradeBot US Stocks - Main Entry Point
=============================================

Multi-Agent trading bot for US stocks using:
- Alpaca API for data and execution
- Multi-timeframe technical analysis
- LONG ONLY strategy (只做多，不做空)

Usage:
    # Paper trading (recommended for testing)
    python main_stocks.py --paper
    
    # Live trading (use with caution!)
    python main_stocks.py --live

Author: AI Trader Team
Date: 2026-01-11
"""

import asyncio
import os
import sys
import argparse
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Version
VERSION = "v1.0.0-stocks"


class StockTradingBot:
    """
    Multi-Agent Stock Trading Bot
    
    Workflow:
    1. DataSyncAgent: Fetch multi-timeframe data from Alpaca
    2. QuantAnalystAgent: Generate technical signals
    3. LLM Engine (optional): Make trading decisions
    4. AlpacaTrader: Execute trades
    """
    
    def __init__(
        self,
        paper: bool = True,
        max_position_size: float = 1000.0,
        stop_loss_pct: float = 2.0,
        take_profit_pct: float = 4.0
    ):
        """
        Initialize Stock Trading Bot
        
        Args:
            paper: True for paper trading, False for live
            max_position_size: Max position size in USD
            stop_loss_pct: Stop loss percentage
            take_profit_pct: Take profit percentage
        """
        print("\n" + "=" * 60)
        print(f"🤖 LLM-TradeBot US Stocks ({VERSION})")
        print("=" * 60)
        
        self.paper = paper
        self.max_position_size = max_position_size
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        
        # Initialize components
        print("\n🚀 Initializing components...")
        
        from src.api.alpaca_client import AlpacaClient
        from src.api.alpaca_trader import AlpacaTrader
        from src.agents.data_sync_agent import DataSyncAgent
        from src.agents.quant_analyst_agent import QuantAnalystAgent
        from src.agents.stock_selector_agent import StockSelectorAgent
        from src.utils.market_hours import MarketHours
        
        self.data_client = AlpacaClient()
        self.trader = AlpacaTrader(paper=paper)
        self.data_agent = DataSyncAgent(self.data_client)
        self.quant_analyst = QuantAnalystAgent()
        self.stock_selector = StockSelectorAgent(use_cache=True)
        self.market_hours = MarketHours()
        
        print(f"  ✅ AlpacaClient ready")
        print(f"  ✅ AlpacaTrader ready ({'PAPER' if paper else '🔴 LIVE'})")
        print(f"  ✅ DataSyncAgent ready")
        print(f"  ✅ QuantAnalystAgent ready")
        print(f"  ✅ StockSelectorAgent ready")
        print(f"  ✅ MarketHours ready")
        
        # 自动选股 (所有股票必须经过动量筛选，包括 Magnificent 7)
        print("\n📊 动量选股中...")
        self.symbols = self.stock_selector.get_momentum_candidates(
            top_n=10,
            min_volume_ratio=1.0,
            min_price_ratio=1.0
        )
        
        print(f"\n⚙️  Trading Config:")
        print(f"  - Symbols: {', '.join(self.symbols)}")
        print(f"  - Max Position: ${self.max_position_size:.2f}")
        print(f"  - Stop Loss: {self.stop_loss_pct}%")
        print(f"  - Take Profit: {self.take_profit_pct}%")
        print(f"  - Mode: {'Paper Trading' if self.paper else '🔴 Live Trading'}")
        
        # State
        self.running = False
        self.cycle_count = 0
    
    async def run_trading_cycle(self, symbol: str) -> Dict:
        """
        Run a single trading cycle for a symbol
        
        Returns:
            Dict with cycle results
        """
        self.cycle_count += 1
        
        print(f"\n{'='*60}")
        print(f"🔄 Cycle #{self.cycle_count} | {symbol} | {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*60}")
        
        result = {
            'symbol': symbol,
            'cycle': self.cycle_count,
            'status': 'completed',
            'action': 'hold',
            'details': {}
        }
        
        try:
            # Step 1: Check market hours
            if not self.market_hours.is_market_open(include_extended=True):
                status = self.market_hours.format_status()
                print(f"📅 Market Status: {status}")
                result['status'] = 'market_closed'
                result['details']['market_status'] = status
                return result
            
            # Step 2: Fetch data
            print("\n📊 Fetching market data...")
            snapshot = await self.data_agent.fetch_all_timeframes(symbol, limit=100)
            
            if not self.data_agent.is_data_ready(snapshot):
                print("⚠️ Data not ready, skipping cycle")
                result['status'] = 'data_not_ready'
                return result
            
            current_price = self.data_agent.get_current_price(snapshot)
            result['details']['price'] = current_price
            
            # Step 3: Analyze
            print("\n📈 Running technical analysis...")
            signal = self.quant_analyst.analyze(
                snapshot.stable_5m,
                snapshot.stable_15m,
                snapshot.stable_1h
            )
            
            print(f"  Signal: {signal.signal_type.value}")
            print(f"  Score: {signal.score:+.1f}")
            print(f"  Confidence: {signal.confidence:.1%}")
            print(f"  Regime: {signal.regime.value}")
            
            result['details']['signal'] = signal.to_dict()
            
            # Step 4: Check existing position
            position = await self.trader.get_position(symbol)
            
            if position:
                print(f"\n💼 Existing position: {position.qty} shares @ ${position.avg_entry_price:.2f}")
                print(f"   PnL: ${position.unrealized_pnl:+.2f} ({position.unrealized_pnl_pct:+.1f}%)")
                
                result['details']['position'] = position.to_dict()
                
                # Check if we should close
                if self._should_close_position(position, signal):
                    print(f"\n🔄 Closing position...")
                    await self.trader.close_position(symbol)
                    result['action'] = 'close'
                    print(f"  ✅ Position closed")
                
                return result
            
            # Step 5: Check for entry
            if signal.confidence >= 0.6:
                action = self._determine_action(signal)
                
                if action != 'hold':
                    print(f"\n🎯 Entry signal: {action.upper()}")
                    
                    # Calculate position size
                    qty = self._calculate_position_size(current_price)
                    
                    if qty > 0:
                        # Calculate stops (LONG only)
                        stop_loss = self.quant_analyst.get_stop_loss_price(
                            snapshot.stable_5m, "LONG"
                        )
                        take_profit = self.quant_analyst.get_take_profit_price(
                            snapshot.stable_5m, "LONG"
                        )
                        
                        print(f"  Quantity: {qty} shares")
                        print(f"  Entry: ${current_price:.2f}")
                        print(f"  Stop-Loss: ${stop_loss:.2f}" if stop_loss else "  Stop-Loss: N/A")
                        print(f"  Take-Profit: ${take_profit:.2f}" if take_profit else "  Take-Profit: N/A")
                        
                        # Execute BUY order (LONG ONLY for US stocks)
                        if action == 'buy':
                            order = await self.trader.open_long(
                                symbol, qty,
                                stop_loss_price=stop_loss,
                                take_profit_price=take_profit
                            )
                            result['action'] = action
                            result['details']['order'] = order.to_dict() if order else None
                            print(f"  ✅ Order placed: {order.id[:8]}..." if order else "  ⚠️ Order failed")
                        else:
                            # No short selling for US stocks
                            print(f"  ⚠️ Sell signal ignored (no short selling)")
            else:
                print(f"\n⏸️ Low confidence ({signal.confidence:.1%}), holding...")
            
            return result
            
        except Exception as e:
            print(f"\n❌ Error in trading cycle: {e}")
            result['status'] = 'error'
            result['details']['error'] = str(e)
            return result
    
    def _determine_action(self, signal) -> str:
        """Determine trade action from signal (LONG ONLY)"""
        from src.agents.quant_analyst_agent import SignalType
        
        # Only BUY signals for US stocks (no shorting)
        if signal.signal_type in (SignalType.STRONG_BUY, SignalType.BUY):
            return 'buy'
        # Sell signals are for closing positions, not opening shorts
        return 'hold'
    
    def _should_close_position(self, position, signal) -> bool:
        """Determine if we should close a LONG position"""
        from src.agents.quant_analyst_agent import SignalType
        
        # Only handle long positions (US stocks = long only)
        if position.side != 'long':
            return False
        
        # Close long if strong sell signal
        if signal.signal_type == SignalType.STRONG_SELL:
            print(f"  📉 Strong sell signal - closing position")
            return True
        
        # Close if take-profit hit
        if position.unrealized_pnl_pct >= self.take_profit_pct:
            print(f"  📈 Take profit triggered at {position.unrealized_pnl_pct:.1f}%")
            return True
        
        # Close if stop-loss hit
        if position.unrealized_pnl_pct <= -self.stop_loss_pct:
            print(f"  📉 Stop loss triggered at {position.unrealized_pnl_pct:.1f}%")
            return True
        
        return False
    
    def _calculate_position_size(self, price: float) -> int:
        """Calculate position size in shares"""
        if price <= 0:
            return 0
        
        # Calculate shares based on max position size
        shares = int(self.max_position_size / price)
        
        # Minimum 1 share
        return max(1, shares)
    
    async def run_continuous(self, interval_seconds: int = 300):
        """
        Run continuous trading loop
        
        Args:
            interval_seconds: Seconds between cycles (default: 5 minutes)
        """
        print(f"\n🚀 Starting continuous trading (interval: {interval_seconds}s)")
        print("   Press Ctrl+C to stop\n")
        
        self.running = True
        
        try:
            while self.running:
                for symbol in self.symbols:
                    if not self.running:
                        break
                    
                    await self.run_trading_cycle(symbol)
                    
                    # Small delay between symbols
                    if self.running:
                        await asyncio.sleep(2)
                
                if self.running:
                    print(f"\n⏰ Next cycle in {interval_seconds}s...")
                    await asyncio.sleep(interval_seconds)
                    
        except KeyboardInterrupt:
            print("\n\n⛔ Stopping bot...")
            self.running = False
        
        await self.cleanup()
    
    async def cleanup(self):
        """Cleanup resources"""
        print("\n🧹 Cleaning up...")
        await self.data_client.close()
        await self.trader.close()
        print("✅ Cleanup complete")


async def main():
    parser = argparse.ArgumentParser(description="LLM-TradeBot US Stocks (自动选股)")
    parser.add_argument("--paper", action="store_true", default=True, help="Use paper trading (default)")
    parser.add_argument("--live", action="store_true", help="Use live trading (dangerous!)")
    parser.add_argument("--interval", type=int, default=300, help="Cycle interval in seconds")
    parser.add_argument("--single", action="store_true", help="Run single cycle and exit")
    
    args = parser.parse_args()
    
    # Determine mode
    paper = not args.live
    
    if not paper:
        print("\n⚠️  WARNING: Live trading mode!")
        print("    Real money is at risk. Are you sure? (y/N)")
        confirm = input().strip().lower()
        if confirm != 'y':
            print("Aborted.")
            return
    
    # Create bot (自动选股)
    bot = StockTradingBot(
        paper=paper,
        max_position_size=1000.0,
        stop_loss_pct=2.0,
        take_profit_pct=4.0
    )
    
    # Run
    if args.single:
        for symbol in bot.symbols:
            await bot.run_trading_cycle(symbol)
        await bot.cleanup()
    else:
        await bot.run_continuous(interval_seconds=args.interval)


if __name__ == "__main__":
    asyncio.run(main())
