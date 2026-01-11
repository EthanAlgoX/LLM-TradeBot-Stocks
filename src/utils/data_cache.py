"""
Data Cache for US Stocks
========================

Caches historical bar data locally for faster access.
Wraps AlpacaClient with caching layer.

Author: AI Trader Team
Date: 2026-01-11
"""

import os
from typing import List, Optional
from datetime import datetime, timedelta
import pandas as pd
from dataclasses import dataclass

from src.api.alpaca_client import AlpacaClient, Bar


class DataCache:
    """
    Caching layer for stock market data
    
    Uses AlpacaClient for data fetching with local caching.
    """
    
    def __init__(self, cache_dir: str = "data/stock_cache"):
        """
        Initialize data cache
        
        Args:
            cache_dir: Directory for cache files
        """
        self.cache_dir = cache_dir
        self.client = AlpacaClient()
        self._memory_cache = {}
        
        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)
    
    def get_bars(
        self,
        symbol: str,
        timeframe: str,
        days: int = 30,
        use_cache: bool = True
    ) -> List[Bar]:
        """
        Get historical bars with caching
        
        Args:
            symbol: Stock symbol
            timeframe: Timeframe ('1m', '5m', '15m', '1h', '1d', '1w')
            days: Number of days of history
            use_cache: Whether to use cache
            
        Returns:
            List of Bar objects
        """
        cache_key = f"{symbol}_{timeframe}_{days}"
        
        # Check memory cache (valid for 5 minutes)
        if use_cache and cache_key in self._memory_cache:
            cached_time, cached_bars = self._memory_cache[cache_key]
            if datetime.now() - cached_time < timedelta(minutes=5):
                return cached_bars
        
        # Fetch from API
        end = datetime.now()
        start = end - timedelta(days=days)
        
        bars = self.client.get_bars(
            symbol=symbol,
            timeframe=timeframe,
            start=start,
            end=end,
            limit=1000
        )
        
        # Update memory cache
        if bars:
            self._memory_cache[cache_key] = (datetime.now(), bars)
        
        return bars
    
    def to_dataframe(self, bars: List[Bar]) -> pd.DataFrame:
        """
        Convert list of bars to pandas DataFrame
        
        Args:
            bars: List of Bar objects
            
        Returns:
            DataFrame with OHLCV columns and datetime index
        """
        return self.client.to_dataframe(bars)
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get latest trade price"""
        return self.client.get_latest_price(symbol)
    
    def clear_cache(self):
        """Clear memory cache"""
        self._memory_cache.clear()
