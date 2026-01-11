#!/usr/bin/env python3
"""
US Stock Trading Demo (Official SDK)
=====================================

Simple demo script to test Alpaca integration using official alpaca-py SDK.
Run this to verify your API keys and data fetching work correctly.

Usage:
    python demo_stocks.py

Author: AI Trader Team
Date: 2026-01-11
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def main():
    print("=" * 60)
    print("🇺🇸 LLM-TradeBot US Stocks - Demo (Official SDK)")
    print("=" * 60)
    
    # Check API keys
    api_key = os.environ.get('ALPACA_API_KEY', '')
    secret_key = os.environ.get('ALPACA_SECRET_KEY', '')
    
    if not api_key or not secret_key or api_key == '你的API_KEY':
        print("\n❌ Alpaca API keys not configured!")
        print("Please set ALPACA_API_KEY and ALPACA_SECRET_KEY in your .env file")
        print("\nGet your free API keys from: https://app.alpaca.markets/")
        return
    
    print(f"\n✅ API Key configured: {api_key[:8]}...{api_key[-4:]}")
    
    # Test Market Hours
    print("\n" + "=" * 40)
    print("📅 Market Hours Check")
    print("=" * 40)
    
    try:
        from src.utils.market_hours import MarketHours
        hours = MarketHours()
        print(f"Status: {hours.format_status()}")
        print(f"Session: {hours.get_current_session().value}")
        print(f"Is Trading Day: {hours.is_trading_day()}")
    except Exception as e:
        print(f"⚠️ Market hours check failed: {e}")
    
    # Test Data Fetching with Official SDK
    print("\n" + "=" * 40)
    print("📊 Data Fetching Test (Official SDK)")
    print("=" * 40)
    
    try:
        from src.api.alpaca_client import AlpacaClient
        client = AlpacaClient()
        
        if not client._client:
            print("❌ Client not initialized - check API keys")
            return
        
        symbols = ["AAPL", "TSLA", "NVDA"]
        
        for symbol in symbols:
            try:
                bars = client.get_bars(symbol, "1d", limit=3)
                if bars:
                    latest = bars[-1]
                    print(f"\n{symbol}:")
                    print(f"  Last Price: ${latest.close:.2f}")
                    print(f"  Volume: {latest.volume:,}")
                    print(f"  Time: {latest.timestamp}")
                else:
                    print(f"\n{symbol}: No data")
            except Exception as e:
                print(f"\n{symbol}: Error - {e}")
        
        # Test quote
        print("\n📈 Getting live quotes...")
        for symbol in symbols[:2]:
            quote = client.get_quote(symbol)
            if quote:
                print(f"  {symbol}: Bid ${quote.bid_price:.2f} / Ask ${quote.ask_price:.2f}")
                
    except Exception as e:
        print(f"❌ Data fetching failed: {e}")
    
    # Test Account Info (Paper Trading)
    print("\n" + "=" * 40)
    print("💰 Account Info (Paper Trading)")
    print("=" * 40)
    
    try:
        from src.api.alpaca_trader import AlpacaTrader
        trader = AlpacaTrader(paper=True)
        
        if not trader._client:
            print("❌ Trader not initialized - check API keys")
            return
        
        account = trader.get_account()
        print(f"Account ID: {account.id[:8]}...")
        print(f"Equity: ${account.equity:,.2f}")
        print(f"Cash: ${account.cash:,.2f}")
        print(f"Buying Power: ${account.buying_power:,.2f}")
        
        # Check positions
        positions = trader.get_positions()
        if positions:
            print(f"\nOpen Positions: {len(positions)}")
            for pos in positions:
                pnl_sign = "+" if pos.unrealized_pnl >= 0 else ""
                print(f"  {pos.symbol}: {pos.qty} shares @ ${pos.avg_entry_price:.2f} (PnL: {pnl_sign}${pos.unrealized_pnl:.2f})")
        else:
            print("\nNo open positions")
            
    except Exception as e:
        print(f"❌ Account error: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Demo Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Ensure your .env file has valid Alpaca API keys")
    print("2. Run the bot: python main_stocks.py --paper --single")
    print("3. For continuous trading: python main_stocks.py --paper")


if __name__ == "__main__":
    main()
