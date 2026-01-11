"""
Unified Market Client for Stock Trading
========================================

Provides a unified interface compatible with the existing codebase
but using Alpaca API for US stock data.

This adapter replaces BinanceClient for stock trading scenarios.

Author: AI Trader Team
Date: 2026-01-11
"""

import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd
from dotenv import load_dotenv

load_dotenv()


class MarketClient:
    """
    Unified Market Client for US Stocks
    
    Provides the same interface as BinanceClient but uses Alpaca API.
    This allows seamless integration with existing agents.
    """
    
    def __init__(self):
        """Initialize market client with Alpaca"""
        from src.api.alpaca_client import AlpacaClient
        
        self._alpaca = AlpacaClient()
        self._cache = {}
        self._cache_time = {}
        
    def get_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 500,
        start_time: int = None
    ) -> List[Dict]:
        """
        Get K-line (candlestick) data
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            interval: Timeframe ('1m', '5m', '15m', '1h', '1d')
            limit: Number of candles
            start_time: Start timestamp in milliseconds (optional)
            
        Returns:
            List of kline dicts with keys: timestamp, open, high, low, close, volume
        """
        # Convert start_time from ms to datetime if provided
        start = None
        if start_time:
            start = datetime.fromtimestamp(start_time / 1000)
        
        bars = self._alpaca.get_bars(
            symbol=symbol,
            timeframe=interval,
            limit=limit,
            start=start
        )
        
        # Convert to Binance-compatible format
        klines = []
        for bar in bars:
            klines.append({
                'timestamp': int(bar.timestamp.timestamp() * 1000),
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume,
                'close_time': int(bar.timestamp.timestamp() * 1000) + self._interval_ms(interval),
                'is_closed': True  # Historical bars are always closed
            })
        
        return klines
    
    def _interval_ms(self, interval: str) -> int:
        """Convert interval to milliseconds"""
        intervals = {
            '1m': 60 * 1000,
            '5m': 5 * 60 * 1000,
            '15m': 15 * 60 * 1000,
            '30m': 30 * 60 * 1000,
            '1h': 60 * 60 * 1000,
            '4h': 4 * 60 * 60 * 1000,
            '1d': 24 * 60 * 60 * 1000,
            '1w': 7 * 24 * 60 * 60 * 1000,
        }
        return intervals.get(interval, 5 * 60 * 1000)
    
    def get_ticker_price(self, symbol: str) -> Dict:
        """
        Get latest ticker price
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dict with 'symbol' and 'price'
        """
        price = self._alpaca.get_latest_price(symbol)
        return {
            'symbol': symbol,
            'price': price or 0.0
        }
    
    def get_funding_rate(self, symbol: str) -> Dict:
        """
        Get funding rate (N/A for stocks, returns mock data)
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dict with mock funding data (stocks don't have funding rates)
        """
        return {
            'symbol': symbol,
            'fundingRate': 0.0,
            'fundingTime': int(datetime.now().timestamp() * 1000),
            'markPrice': 0.0
        }
    
    def get_funding_rate_with_cache(self, symbol: str) -> Dict:
        """Get funding rate with caching (returns mock for stocks)"""
        return self.get_funding_rate(symbol)
    
    def get_open_interest(self, symbol: str) -> Dict:
        """
        Get open interest (N/A for stocks)
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Empty dict (stocks don't have OI like futures)
        """
        return {}
    
    def get_account_balance(self) -> float:
        """
        Get account balance
        
        Returns:
            Available cash balance
        """
        from src.api.alpaca_trader import AlpacaTrader
        trader = AlpacaTrader(paper=True)
        account = trader.get_account()
        return float(account.cash) if account else 0.0
    
    def get_orderbook(self, symbol: str, limit: int = 20) -> Dict:
        """
        Get order book (simplified for stocks)
        
        Args:
            symbol: Stock symbol
            limit: Depth limit
            
        Returns:
            Dict with bids and asks from quote
        """
        quote = self._alpaca.get_quote(symbol)
        if quote:
            return {
                'bids': [[quote.bid_price, quote.bid_size]],
                'asks': [[quote.ask_price, quote.ask_size]]
            }
        return {'bids': [], 'asks': []}
    
    def get_market_data_snapshot(self, symbol: str) -> Dict:
        """
        Get complete market data snapshot
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dict with price, quote, and account info
        """
        price = self._alpaca.get_latest_price(symbol) or 0.0
        quote = self._alpaca.get_quote(symbol)
        
        return {
            'symbol': symbol,
            'price': price,
            'bid': quote.bid_price if quote else 0.0,
            'ask': quote.ask_price if quote else 0.0,
            'volume': 0,  # Would need bars to get volume
            'timestamp': datetime.now().isoformat()
        }


# Alias for backward compatibility
BinanceClient = MarketClient
