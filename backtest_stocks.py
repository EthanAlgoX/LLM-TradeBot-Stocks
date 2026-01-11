#!/usr/bin/env python3
"""
US Stock Backtester
===================

Backtest trading strategies on historical US stock data from Alpaca.

Usage:
    # Backtest on AAPL daily data for the last 30 days
    python backtest_stocks.py --symbol AAPL --interval 1d --days 30
    
    # Backtest on multiple symbols
    python backtest_stocks.py --symbols AAPL,TSLA,NVDA --interval 1h --days 7

Author: AI Trader Team
Date: 2026-01-11
"""

import argparse
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import pandas as pd
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Trade:
    """Single trade record"""
    symbol: str
    side: str  # 'buy' or 'sell'
    entry_time: datetime
    entry_price: float
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    quantity: float = 1.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    reason: str = ""
    
    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'side': self.side,
            'entry_time': self.entry_time.isoformat() if self.entry_time else None,
            'entry_price': self.entry_price,
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'exit_price': self.exit_price,
            'quantity': self.quantity,
            'pnl': self.pnl,
            'pnl_pct': self.pnl_pct,
            'reason': self.reason
        }


@dataclass 
class BacktestResult:
    """Backtest result summary"""
    symbol: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    total_return: float
    total_return_pct: float
    num_trades: int
    win_rate: float
    max_drawdown: float
    sharpe_ratio: float
    trades: List[Trade]
    
    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'initial_capital': self.initial_capital,
            'final_capital': self.final_capital,
            'total_return': self.total_return,
            'total_return_pct': self.total_return_pct,
            'num_trades': self.num_trades,
            'win_rate': self.win_rate,
            'max_drawdown': self.max_drawdown,
            'sharpe_ratio': self.sharpe_ratio,
            'trades': [t.to_dict() for t in self.trades]
        }


class StockBacktester:
    """
    Stock Trading Strategy Backtester
    
    Uses historical data from Alpaca and applies QuantAnalystAgent signals.
    """
    
    def __init__(
        self,
        initial_capital: float = 10000.0,
        position_size_pct: float = 10.0,
        stop_loss_pct: float = 2.0,
        take_profit_pct: float = 4.0
    ):
        self.initial_capital = initial_capital
        self.position_size_pct = position_size_pct
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        
        # Initialize components
        from src.api.alpaca_client import AlpacaClient
        from src.agents.quant_analyst_agent import QuantAnalystAgent
        
        self.client = AlpacaClient()
        self.analyst = QuantAnalystAgent()
    
    def fetch_historical_data(
        self,
        symbol: str,
        interval: str,
        days: int
    ) -> pd.DataFrame:
        """Fetch historical data for backtesting"""
        print(f"📊 Fetching {days} days of {interval} data for {symbol}...")
        
        # For backtesting, we need to go back far enough to get data
        # IEX free tier has delayed data, so we go back further
        from datetime import datetime, timedelta
        
        # End date should be a few days ago to ensure data is available
        end_date = datetime.now() - timedelta(days=2)
        start_date = end_date - timedelta(days=days + 10)  # Extra buffer for weekends
        
        # Calculate limit based on interval
        if interval in ['1m', '5m']:
            limit = days * 78 * (60 // int(interval.replace('m', '')))
        elif interval in ['15m', '30m']:
            limit = days * 78 * (60 // int(interval.replace('m', '')))
        elif interval in ['1h', '4h']:
            limit = days * 7 * (24 // int(interval.replace('h', '')))
        else:  # 1d
            limit = days * 2
        
        limit = min(limit, 1000)
        
        bars = self.client.get_bars(symbol, interval, limit=limit, start=start_date, end=end_date)
        
        if not bars:
            print(f"⚠️ No data for {symbol}")
            return pd.DataFrame()
        
        # Convert to DataFrame
        data = []
        for bar in bars:
            data.append({
                'timestamp': bar.timestamp,
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume
            })
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        
        # Add indicators
        df = self._add_indicators(df)
        
        print(f"  ✅ Loaded {len(df)} bars from {df.index[0]} to {df.index[-1]}")
        return df
    
    def _add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators to dataframe"""
        if len(df) < 26:
            return df
        
        # EMA
        df['ema_12'] = df['close'].ewm(span=12).mean()
        df['ema_26'] = df['close'].ewm(span=26).mean()
        
        # MACD
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, 1e-10)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        df['bb_mid'] = df['close'].rolling(20).mean()
        df['bb_std'] = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
        df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        import numpy as np
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(14).mean()
        
        # SMA
        df['sma_20'] = df['close'].rolling(20).mean()
        df['sma_50'] = df['close'].rolling(50).mean()
        
        return df
    
    def run_backtest(
        self,
        symbol: str,
        interval: str = '1d',
        days: int = 30
    ) -> BacktestResult:
        """
        Run backtest on a single symbol
        """
        print(f"\n{'='*60}")
        print(f"🔄 Backtesting {symbol} | {interval} | {days} days")
        print(f"{'='*60}")
        
        # Fetch data
        df = self.fetch_historical_data(symbol, interval, days)
        
        if df.empty or len(df) < 30:
            print("❌ Insufficient data for backtest")
            return BacktestResult(
                symbol=symbol,
                start_date=datetime.now(),
                end_date=datetime.now(),
                initial_capital=self.initial_capital,
                final_capital=self.initial_capital,
                total_return=0,
                total_return_pct=0,
                num_trades=0,
                win_rate=0,
                max_drawdown=0,
                sharpe_ratio=0,
                trades=[]
            )
        
        # Initialize state
        capital = self.initial_capital
        position = None  # Current position
        trades = []
        equity_curve = [capital]
        
        # Skip warmup period (first 30 bars)
        warmup = 30
        
        print(f"\n📈 Running simulation...")
        
        for i in range(warmup, len(df)):
            current_bar = df.iloc[i]
            history = df.iloc[max(0, i-100):i+1]
            
            price = current_bar['close']
            timestamp = df.index[i]
            
            # Check existing position
            if position:
                # Check stop-loss
                if position['side'] == 'long':
                    pnl_pct = (price - position['entry_price']) / position['entry_price'] * 100
                    
                    if pnl_pct <= -self.stop_loss_pct:
                        # Stop-loss hit
                        pnl = (price - position['entry_price']) * position['quantity']
                        capital += pnl
                        trades.append(Trade(
                            symbol=symbol,
                            side='long',
                            entry_time=position['entry_time'],
                            entry_price=position['entry_price'],
                            exit_time=timestamp,
                            exit_price=price,
                            quantity=position['quantity'],
                            pnl=pnl,
                            pnl_pct=pnl_pct,
                            reason='stop_loss'
                        ))
                        position = None
                    
                    elif pnl_pct >= self.take_profit_pct:
                        # Take-profit hit
                        pnl = (price - position['entry_price']) * position['quantity']
                        capital += pnl
                        trades.append(Trade(
                            symbol=symbol,
                            side='long',
                            entry_time=position['entry_time'],
                            entry_price=position['entry_price'],
                            exit_time=timestamp,
                            exit_price=price,
                            quantity=position['quantity'],
                            pnl=pnl,
                            pnl_pct=pnl_pct,
                            reason='take_profit'
                        ))
                        position = None
            
            # Generate signal if no position
            if not position:
                signal = self._generate_signal(history)
                
                if signal == 'buy' and capital > 0:
                    # Calculate position size
                    position_value = capital * (self.position_size_pct / 100)
                    quantity = position_value / price
                    
                    position = {
                        'side': 'long',
                        'entry_time': timestamp,
                        'entry_price': price,
                        'quantity': quantity
                    }
            
            # Track equity
            if position:
                unrealized_pnl = (price - position['entry_price']) * position['quantity']
                equity_curve.append(capital + unrealized_pnl)
            else:
                equity_curve.append(capital)
        
        # Close any remaining position at end
        if position:
            final_price = df.iloc[-1]['close']
            pnl = (final_price - position['entry_price']) * position['quantity']
            capital += pnl
            trades.append(Trade(
                symbol=symbol,
                side='long',
                entry_time=position['entry_time'],
                entry_price=position['entry_price'],
                exit_time=df.index[-1],
                exit_price=final_price,
                quantity=position['quantity'],
                pnl=pnl,
                pnl_pct=(final_price - position['entry_price']) / position['entry_price'] * 100,
                reason='end_of_backtest'
            ))
        
        # Calculate metrics
        total_return = capital - self.initial_capital
        total_return_pct = (total_return / self.initial_capital) * 100
        
        winning_trades = [t for t in trades if t.pnl > 0]
        win_rate = len(winning_trades) / len(trades) * 100 if trades else 0
        
        # Max drawdown
        equity_series = pd.Series(equity_curve)
        rolling_max = equity_series.expanding().max()
        drawdown = (equity_series - rolling_max) / rolling_max * 100
        max_drawdown = abs(drawdown.min())
        
        # Sharpe ratio (simplified)
        returns = equity_series.pct_change().dropna()
        sharpe_ratio = returns.mean() / returns.std() * (252 ** 0.5) if returns.std() > 0 else 0
        
        result = BacktestResult(
            symbol=symbol,
            start_date=df.index[warmup],
            end_date=df.index[-1],
            initial_capital=self.initial_capital,
            final_capital=capital,
            total_return=total_return,
            total_return_pct=total_return_pct,
            num_trades=len(trades),
            win_rate=win_rate,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            trades=trades
        )
        
        # Print results
        self._print_results(result)
        
        return result
    
    def _generate_signal(self, df: pd.DataFrame) -> Optional[str]:
        """Generate signal using optimized stock strategy"""
        if len(df) < 50:
            return None
        
        try:
            from src.strategy.stock_strategy import StockStrategy
            strategy = StockStrategy(
                base_position_size=self.position_size_pct,
                max_risk_per_trade=self.stop_loss_pct
            )
            
            setup = strategy.analyze(df, symbol='STOCK')
            
            if setup and setup.confidence >= 0.5:
                if setup.direction == 'long':
                    return 'buy'
                elif setup.direction == 'short':
                    return 'sell'
        except Exception as e:
            # Fallback to simple strategy
            pass
        
        # Fallback: Simple strategy
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        rsi = current.get('rsi', 50)
        macd_hist = current.get('macd_hist', 0)
        prev_macd_hist = prev.get('macd_hist', 0)
        
        buy_signals = 0
        
        if pd.notna(rsi) and rsi < 35:
            buy_signals += 1
        
        if pd.notna(macd_hist) and pd.notna(prev_macd_hist):
            if prev_macd_hist < 0 and macd_hist > 0:
                buy_signals += 2
        
        if current['close'] > current.get('sma_20', 0) and pd.notna(current.get('sma_20', None)):
            buy_signals += 1
        
        if buy_signals >= 2:
            return 'buy'
        
        return None
    
    def _print_results(self, result: BacktestResult):
        """Print backtest results"""
        print(f"\n{'='*60}")
        print(f"📊 Backtest Results: {result.symbol}")
        print(f"{'='*60}")
        print(f"Period: {result.start_date.strftime('%Y-%m-%d')} to {result.end_date.strftime('%Y-%m-%d')}")
        print(f"\n💰 Capital:")
        print(f"  Initial: ${result.initial_capital:,.2f}")
        print(f"  Final:   ${result.final_capital:,.2f}")
        print(f"  Return:  ${result.total_return:+,.2f} ({result.total_return_pct:+.2f}%)")
        
        print(f"\n📈 Performance:")
        print(f"  Trades:       {result.num_trades}")
        print(f"  Win Rate:     {result.win_rate:.1f}%")
        print(f"  Max Drawdown: {result.max_drawdown:.2f}%")
        print(f"  Sharpe Ratio: {result.sharpe_ratio:.2f}")
        
        if result.trades:
            print(f"\n📋 Trades:")
            for t in result.trades[-5:]:  # Last 5 trades
                sign = "+" if t.pnl > 0 else ""
                exit_price_str = f"${t.exit_price:.2f}" if t.exit_price else "Open"
                exit_time_str = t.exit_time.strftime('%m-%d') if t.exit_time else 'Open'
                print(f"  {t.entry_time.strftime('%m-%d')} → {exit_time_str}: "
                      f"${t.entry_price:.2f} → {exit_price_str} | "
                      f"{sign}${t.pnl:.2f} ({sign}{t.pnl_pct:.1f}%) [{t.reason}]")
    
    def save_results(self, result: BacktestResult, session_dir: str):
        """
        Save backtest results to structured file system
        
        Structure:
        data/backtest_cache/{session_datetime}/
            ├── summary.json  (overall session summary)
            └── {date}_{symbol}.json  (per-stock results)
        
        Args:
            result: BacktestResult object
            session_dir: Session directory path
        """
        # Create session directory if not exists
        os.makedirs(session_dir, exist_ok=True)
        
        # Generate per-stock filename: {date}_{symbol}.json
        date_str = result.start_date.strftime('%Y%m%d')
        symbol_file = os.path.join(session_dir, f"{date_str}_{result.symbol}.json")
        
        # Save per-stock result
        result_data = result.to_dict()
        result_data['saved_at'] = datetime.now().isoformat()
        
        with open(symbol_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Results saved: {symbol_file}")
        
        return symbol_file


def main():
    parser = argparse.ArgumentParser(description="US Stock Backtester")
    parser.add_argument("--symbol", type=str, default="AAPL", help="Single symbol to backtest")
    parser.add_argument("--symbols", type=str, help="Comma-separated symbols")
    parser.add_argument("--interval", type=str, default="1d", help="Timeframe (1d, 1h, 15m)")
    parser.add_argument("--days", type=int, default=60, help="Days of history")
    parser.add_argument("--capital", type=float, default=10000, help="Initial capital")
    
    args = parser.parse_args()
    
    symbols = args.symbols.split(",") if args.symbols else [args.symbol]
    
    # Create session directory: data/backtest_cache/{datetime}/
    session_time = datetime.now().strftime('%Y%m%d_%H%M%S')
    session_dir = os.path.join('data', 'backtest_cache', session_time)
    os.makedirs(session_dir, exist_ok=True)
    
    print(f"\n📂 Session directory: {session_dir}")
    
    backtester = StockBacktester(
        initial_capital=args.capital,
        position_size_pct=10.0,
        stop_loss_pct=2.0,
        take_profit_pct=4.0
    )
    
    results = []
    for symbol in symbols:
        symbol = symbol.strip()
        try:
            result = backtester.run_backtest(symbol, args.interval, args.days)
            if result:
                # Save result to session directory
                backtester.save_results(result, session_dir)
                results.append(result)
        except Exception as e:
            print(f"❌ Error backtesting {symbol}: {e}")
    
    # Save session summary
    if results:
        summary = {
            'session_time': session_time,
            'symbols': [r.symbol for r in results],
            'interval': args.interval,
            'days': args.days,
            'capital': args.capital,
            'total_return_pct': sum(r.total_return_pct for r in results) / len(results),
            'total_trades': sum(r.num_trades for r in results)
        }
        summary_file = os.path.join(session_dir, 'summary.json')
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"\n📊 Session summary saved: {summary_file}")


if __name__ == "__main__":
    main()
