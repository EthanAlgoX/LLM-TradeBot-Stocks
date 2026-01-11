"""
Stock Selector Agent
====================

Dynamically selects stocks based on momentum indicators.
Filters by volume ratio, price ratio, and other criteria.

Author: AI Trader Team
Date: 2026-01-11
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import os


@dataclass
class StockCandidate:
    """Stock candidate with momentum metrics"""
    symbol: str
    price: float
    volume: int
    avg_volume: int
    volume_ratio: float
    price_change_pct: float
    score: float
    
    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'price': self.price,
            'volume': self.volume,
            'avg_volume': self.avg_volume,
            'volume_ratio': self.volume_ratio,
            'price_change_pct': self.price_change_pct,
            'score': self.score
        }


class StockSelectorAgent:
    """
    Dynamic Stock Selection Agent
    
    Selects stocks based on:
    - Volume ratio (today's volume / average volume)
    - Price ratio (momentum)
    - Market cap filters
    """
    
    # Magnificent 7 stocks
    MAG7 = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA']
    
    # Additional high-volume tech stocks
    TECH_STOCKS = ['AMD', 'INTC', 'CRM', 'ORCL', 'ADBE', 'NFLX', 'PYPL', 'SQ', 'SHOP', 'UBER']
    
    # Financial stocks
    FINANCIAL_STOCKS = ['JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'V', 'MA']
    
    # Healthcare stocks
    HEALTHCARE_STOCKS = ['JNJ', 'UNH', 'PFE', 'ABBV', 'MRK', 'LLY']
    
    def __init__(self, use_cache: bool = True):
        """
        Initialize stock selector
        
        Args:
            use_cache: Whether to use cached data
        """
        self.use_cache = use_cache
        self._cache = {}
        self._cache_time = None
        
        # Initialize client lazily
        self._client = None
    
    def _get_client(self):
        """Lazy initialization of Alpaca client"""
        if self._client is None:
            from src.api.alpaca_client import AlpacaClient
            self._client = AlpacaClient()
        return self._client
    
    def get_stock_universe(self) -> List[str]:
        """
        Get full stock universe
        
        Returns:
            List of stock symbols
        """
        universe = list(set(
            self.MAG7 + 
            self.TECH_STOCKS + 
            self.FINANCIAL_STOCKS + 
            self.HEALTHCARE_STOCKS
        ))
        return sorted(universe)
    
    def get_momentum_candidates(
        self,
        top_n: int = 10,
        min_volume_ratio: float = 1.0,
        min_price_ratio: float = 1.0,
        include_mag7: bool = True
    ) -> List[str]:
        """
        Get top momentum candidates
        
        All stocks (including Magnificent 7) must meet the momentum criteria.
        
        Args:
            top_n: Number of top candidates to return
            min_volume_ratio: Minimum volume ratio (1.0 = average)
            min_price_ratio: Minimum price ratio (not used currently)
            include_mag7: Whether to include Mag7 in universe
            
        Returns:
            List of top stock symbols sorted by momentum score
        """
        # Check cache
        cache_key = f"{top_n}_{min_volume_ratio}_{min_price_ratio}"
        if self.use_cache and cache_key in self._cache:
            cache_time, cached_result = self._cache[cache_key]
            if datetime.now() - cache_time < timedelta(minutes=15):
                return cached_result
        
        # Get stock universe
        universe = self.get_stock_universe()
        
        # Get client
        client = self._get_client()
        if not client._client:
            # Fallback to Mag7 if no API access
            print("⚠️ No API access, using default Mag7 stocks")
            return self.MAG7[:top_n]
        
        candidates = []
        
        for symbol in universe:
            try:
                # Get recent bars for analysis
                bars = client.get_bars(symbol, '1d', limit=21)
                
                if not bars or len(bars) < 20:
                    continue
                
                # Calculate metrics
                latest = bars[-1]
                prev = bars[-2]
                
                # Volume analysis
                volumes = [b.volume for b in bars[:-1]]  # Exclude today
                avg_volume = sum(volumes) / len(volumes) if volumes else 1
                volume_ratio = latest.volume / avg_volume if avg_volume > 0 else 0
                
                # Price change
                price_change_pct = (latest.close - prev.close) / prev.close * 100 if prev.close > 0 else 0
                
                # Filter by minimum criteria
                if volume_ratio < min_volume_ratio:
                    continue
                
                # Calculate momentum score
                # Higher volume ratio + positive price change = higher score
                score = volume_ratio * (1 + price_change_pct / 100)
                
                candidates.append(StockCandidate(
                    symbol=symbol,
                    price=latest.close,
                    volume=latest.volume,
                    avg_volume=int(avg_volume),
                    volume_ratio=volume_ratio,
                    price_change_pct=price_change_pct,
                    score=score
                ))
                
            except Exception as e:
                print(f"⚠️ Error analyzing {symbol}: {e}")
                continue
        
        # Sort by score descending
        candidates.sort(key=lambda x: x.score, reverse=True)
        
        # Get top N symbols
        top_symbols = [c.symbol for c in candidates[:top_n]]
        
        # Cache result
        self._cache[cache_key] = (datetime.now(), top_symbols)
        
        # Fallback if no candidates found
        if not top_symbols:
            print("⚠️ No momentum candidates found, using default stocks")
            return self.MAG7[:top_n]
        
        return top_symbols
    
    def get_detailed_candidates(
        self,
        top_n: int = 10,
        min_volume_ratio: float = 1.0
    ) -> List[StockCandidate]:
        """
        Get detailed momentum candidates with all metrics
        
        Args:
            top_n: Number of top candidates
            min_volume_ratio: Minimum volume ratio
            
        Returns:
            List of StockCandidate objects with full details
        """
        symbols = self.get_momentum_candidates(
            top_n=top_n * 2,  # Get more for filtering
            min_volume_ratio=min_volume_ratio
        )
        
        # This is simplified - in production, store candidates during get_momentum_candidates
        return []  # Return empty for now, would need to refactor to store candidates
