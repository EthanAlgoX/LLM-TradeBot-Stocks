#!/usr/bin/env python3
"""
Fetch Raw Data
==============

Fetch 15m bars for all 91 watchlist stocks for the last 10 days.
Groups data by day and saves to raw_data directory.
Ensures correct timestamp format (YYYY-MM-DD HH:MM:SS) and timezone.

Usage:
    python fetch_raw_data.py
"""

import os
import sys
import time
from datetime import datetime, timedelta, date
from collections import defaultdict
import pandas as pd
from zoneinfo import ZoneInfo

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.api.alpaca_client import AlpacaClient
from src.utils.data_manager import DataManager
from src.config.watchlist_2026 import ALL_TICKERS

# Initialize
client = AlpacaClient()
dm = DataManager()
ET = ZoneInfo("America/New_York")

def fetch_and_save_data():
    print(f"🚀 Starting data fetch for {len(ALL_TICKERS)} stocks...")
    
    # Range: Last 10 days to cover 7 trading days securely
    end_dt = datetime.now(ET)
    start_dt = end_dt - timedelta(days=12)
    
    print(f"📅 Range: {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}")
    
    success_count = 0
    fail_count = 0
    
    for symbol in ALL_TICKERS:
        try:
            # sys.stdout.write(f"\r⏳ Fetching {symbol}...")
            # sys.stdout.flush()
            
            # Fetch bars
            bars = client.get_bars(
                symbol=symbol,
                timeframe='15m',
                start=start_dt,
                end=end_dt,
                limit=10000
            )
            
            if not bars:
                # print(f" ⚠️ No data for {symbol}")
                fail_count += 1
                continue
                
            # Group by date
            bars_by_date = defaultdict(list)
            
            # Market hours in minutes from midnight
            MARKET_OPEN = 9 * 60 + 30  # 9:30 = 570
            MARKET_CLOSE = 16 * 60     # 16:00 = 960
            
            for bar in bars:
                # Convert to ET for date grouping and formatting
                ts_et = bar.timestamp.astimezone(ET)
                
                # Filter by market hours (09:30 <= time < 16:00)
                minutes = ts_et.hour * 60 + ts_et.minute
                if not (MARKET_OPEN <= minutes < MARKET_CLOSE):
                    continue
                
                trade_date = ts_et.date()
                
                # Format bar data (explicit timestamp format)
                bar_data = {
                    "timestamp": ts_et.strftime('%Y-%m-%d %H:%M:%S'),
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "volume": bar.volume
                }
                bars_by_date[trade_date].append(bar_data)
            
            # Save for each date
            saved_dates = 0
            for trade_date, day_bars in bars_by_date.items():
                dm.save_raw_bars(symbol, '15m', day_bars, trade_date)
                saved_dates += 1
            
            success_count += 1
            if success_count % 10 == 0:
                print(f"✅ Processed {success_count}/{len(ALL_TICKERS)} stocks")
                
        except Exception as e:
            print(f"\n❌ Error {symbol}: {e}")
            fail_count += 1
            time.sleep(1) # Backoff on error
    
    print(f"\n🏁 Finished!")
    print(f"   Success: {success_count}")
    print(f"   Failed:  {fail_count}")

if __name__ == "__main__":
    fetch_and_save_data()
