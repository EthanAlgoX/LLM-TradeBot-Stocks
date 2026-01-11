"""
Alpaca API Client for US Stock Data
====================================

Provides market data access using the official alpaca-py SDK.
Supports multiple timeframes and real-time quotes.

Author: AI Trader Team
Date: 2026-01-11
"""

import os
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import pandas as pd
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Bar:
    """OHLCV bar data"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume
        }


@dataclass
class Quote:
    """Real-time quote data"""
    symbol: str
    bid_price: float
    bid_size: int
    ask_price: float
    ask_size: int
    timestamp: datetime


class AlpacaClient:
    """
    Alpaca Market Data Client
    
    Uses IEX (free) or SIP (paid) data feed.
    Supports historical bars and real-time quotes.
    """
    
    # Timeframe mapping from our format to Alpaca format
    TIMEFRAME_MAP = {
        '1m': '1Min',
        '5m': '5Min',
        '15m': '15Min',
        '30m': '30Min',
        '1h': '1Hour',
        '4h': '4Hour',
        '1d': '1Day',
        '1w': '1Week',
    }
    
    def __init__(self):
        """Initialize Alpaca client with API credentials"""
        self.api_key = os.environ.get('ALPACA_API_KEY', '')
        self.secret_key = os.environ.get('ALPACA_SECRET_KEY', '')
        
        self._client = None
        self._initialized = False
        
        if self.api_key and self.secret_key and self.api_key != '你的API_KEY':
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Alpaca stock client"""
        try:
            from alpaca.data.historical import StockHistoricalDataClient
            
            self._client = StockHistoricalDataClient(
                api_key=self.api_key,
                secret_key=self.secret_key
            )
            self._initialized = True
            
        except Exception as e:
            print(f"⚠️ Failed to initialize Alpaca client: {e}")
            self._client = None
    
    def get_bars(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> List[Bar]:
        """
        Get historical bar data
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            timeframe: Timeframe ('1m', '5m', '15m', '1h', '1d', '1w')
            limit: Number of bars to fetch
            start: Start datetime (optional)
            end: End datetime (optional)
            
        Returns:
            List of Bar objects
        """
        if not self._client:
            return []
        
        try:
            from alpaca.data.requests import StockBarsRequest
            from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
            
            # Map our timeframe to Alpaca TimeFrame
            tf_map = {
                '1m': TimeFrame(1, TimeFrameUnit.Minute),
                '5m': TimeFrame(5, TimeFrameUnit.Minute),
                '15m': TimeFrame(15, TimeFrameUnit.Minute),
                '30m': TimeFrame(30, TimeFrameUnit.Minute),
                '1h': TimeFrame(1, TimeFrameUnit.Hour),
                '4h': TimeFrame(4, TimeFrameUnit.Hour),
                '1d': TimeFrame(1, TimeFrameUnit.Day),
                '1w': TimeFrame(1, TimeFrameUnit.Week),
            }
            
            alpaca_tf = tf_map.get(timeframe, TimeFrame(1, TimeFrameUnit.Day))
            
            # Calculate default start/end if not provided
            # Note: Free tier (IEX) requires data to be at least 15 minutes delayed
            if end is None:
                end = datetime.now() - timedelta(minutes=20)
            if start is None:
                # Calculate start based on timeframe and limit
                if timeframe in ['1m', '5m']:
                    start = end - timedelta(days=7)
                elif timeframe in ['15m', '30m']:
                    start = end - timedelta(days=30)
                elif timeframe in ['1h', '4h']:
                    start = end - timedelta(days=60)
                else:
                    start = end - timedelta(days=365)
            
            # Use IEX feed (free tier)
            from alpaca.data.enums import DataFeed
            
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=alpaca_tf,
                start=start,
                end=end,
                limit=limit,
                feed=DataFeed.IEX
            )
            
            bars_response = self._client.get_stock_bars(request)
            
            # Convert to our Bar format
            bars = []
            if symbol in bars_response.data:
                for bar in bars_response.data[symbol]:
                    bars.append(Bar(
                        timestamp=bar.timestamp,
                        open=float(bar.open),
                        high=float(bar.high),
                        low=float(bar.low),
                        close=float(bar.close),
                        volume=int(bar.volume)
                    ))
            
            return bars[-limit:] if len(bars) > limit else bars
            
        except Exception as e:
            print(f"⚠️ Error fetching bars for {symbol}: {e}")
            return []
    
    def get_quote(self, symbol: str) -> Optional[Quote]:
        """
        Get latest quote for a symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Quote object or None
        """
        if not self._client:
            return None
        
        try:
            from alpaca.data.requests import StockLatestQuoteRequest
            
            request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            quotes = self._client.get_stock_latest_quote(request)
            
            if symbol in quotes:
                q = quotes[symbol]
                return Quote(
                    symbol=symbol,
                    bid_price=float(q.bid_price),
                    bid_size=int(q.bid_size),
                    ask_price=float(q.ask_price),
                    ask_size=int(q.ask_size),
                    timestamp=q.timestamp
                )
            
            return None
            
        except Exception as e:
            print(f"⚠️ Error fetching quote for {symbol}: {e}")
            return None
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get the latest trade price for a symbol"""
        if not self._client:
            return None
        
        try:
            from alpaca.data.requests import StockLatestTradeRequest
            
            request = StockLatestTradeRequest(symbol_or_symbols=symbol)
            trades = self._client.get_stock_latest_trade(request)
            
            if symbol in trades:
                return float(trades[symbol].price)
            
            return None
            
        except Exception as e:
            print(f"⚠️ Error fetching price for {symbol}: {e}")
            return None
    
    def to_dataframe(self, bars: List[Bar]) -> pd.DataFrame:
        """Convert list of bars to pandas DataFrame"""
        if not bars:
            return pd.DataFrame()
        
        data = [b.to_dict() for b in bars]
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        return df
    
    async def close(self):
        """Cleanup (no persistent connections to close)"""
        pass
