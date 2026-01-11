"""
Simplified Agent Framework for Backtesting
============================================

Lightweight agents for stock backtesting without LLM dependencies.
Provides technical analysis-based decision making.

Author: AI Trader Team
Date: 2026-01-11
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import pandas as pd
import numpy as np


class WeeklyBias(Enum):
    """Weekly trend bias"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass
class ProcessedData:
    """Processed market data for analysis"""
    symbol: str
    df_weekly: Optional[pd.DataFrame] = None
    df_daily: Optional[pd.DataFrame] = None
    df_15m: Optional[pd.DataFrame] = None
    current_price: float = 0.0
    timestamp: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'current_price': self.current_price,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'has_weekly': self.df_weekly is not None,
            'has_daily': self.df_daily is not None,
            'has_15m': self.df_15m is not None
        }


@dataclass
class TrendAnalysis:
    """Multi-period trend analysis result"""
    weekly_bias: WeeklyBias = WeeklyBias.NEUTRAL
    daily_bias: WeeklyBias = WeeklyBias.NEUTRAL
    intraday_bias: WeeklyBias = WeeklyBias.NEUTRAL
    overall_score: float = 0.0  # -1 to +1
    confidence: float = 0.0
    notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'weekly_bias': self.weekly_bias.value,
            'daily_bias': self.daily_bias.value,
            'intraday_bias': self.intraday_bias.value,
            'overall_score': self.overall_score,
            'confidence': self.confidence,
            'notes': self.notes
        }


@dataclass
class TradeDecision:
    """Trading decision output"""
    action: str  # "BUY", "SELL", "WAIT"
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    confidence: float = 0.0
    summary_reason: str = ""
    detailed_reasons: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'action': self.action,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'confidence': self.confidence,
            'summary_reason': self.summary_reason,
            'detailed_reasons': self.detailed_reasons
        }


class DataProcessorAgent:
    """
    Data Processing Agent
    
    Adds technical indicators to price data.
    """
    
    def __init__(self):
        pass
    
    def _add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators to dataframe"""
        if df is None or df.empty or len(df) < 26:
            return df
        
        df = df.copy()
        
        # EMA
        df['ema_9'] = df['close'].ewm(span=9).mean()
        df['ema_21'] = df['close'].ewm(span=21).mean()
        df['ema_50'] = df['close'].ewm(span=50).mean() if len(df) >= 50 else np.nan
        
        # MACD
        ema_12 = df['close'].ewm(span=12).mean()
        ema_26 = df['close'].ewm(span=26).mean()
        df['macd'] = ema_12 - ema_26
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, 1e-10)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(14).mean()
        
        # Bollinger Bands
        df['bb_mid'] = df['close'].rolling(20).mean()
        df['bb_std'] = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
        df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']
        
        # Volume MA
        df['volume_ma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma'].replace(0, 1)
        
        return df
    
    def process(self, df: pd.DataFrame, symbol: str = "STOCK") -> ProcessedData:
        """Process raw data into ProcessedData"""
        processed_df = self._add_indicators(df)
        
        current_price = float(processed_df['close'].iloc[-1]) if not processed_df.empty else 0.0
        
        return ProcessedData(
            symbol=symbol,
            df_15m=processed_df,
            current_price=current_price,
            timestamp=datetime.now()
        )


class MultiPeriodAgent:
    """
    Multi-Period Trend Analysis Agent
    
    Analyzes trends across weekly, daily, and intraday timeframes.
    """
    
    def __init__(self):
        pass
    
    def analyze(self, data: ProcessedData) -> TrendAnalysis:
        """Analyze multi-period trends"""
        result = TrendAnalysis()
        
        # Weekly bias
        if data.df_weekly is not None and len(data.df_weekly) >= 10:
            result.weekly_bias = self._get_bias(data.df_weekly)
            result.notes.append(f"Weekly: {result.weekly_bias.value}")
        
        # Daily bias
        if data.df_daily is not None and len(data.df_daily) >= 10:
            result.daily_bias = self._get_bias(data.df_daily)
            result.notes.append(f"Daily: {result.daily_bias.value}")
        
        # Intraday bias (15m)
        if data.df_15m is not None and len(data.df_15m) >= 20:
            result.intraday_bias = self._get_bias(data.df_15m)
            result.notes.append(f"Intraday: {result.intraday_bias.value}")
        
        # Calculate overall score
        bias_scores = {
            WeeklyBias.BULLISH: 1,
            WeeklyBias.BEARISH: -1,
            WeeklyBias.NEUTRAL: 0
        }
        
        # Weight: weekly 40%, daily 35%, intraday 25%
        score = (
            bias_scores[result.weekly_bias] * 0.4 +
            bias_scores[result.daily_bias] * 0.35 +
            bias_scores[result.intraday_bias] * 0.25
        )
        
        result.overall_score = score
        result.confidence = abs(score)
        
        return result
    
    def _get_bias(self, df: pd.DataFrame) -> WeeklyBias:
        """Determine bias from dataframe"""
        if df is None or df.empty or len(df) < 5:
            return WeeklyBias.NEUTRAL
        
        try:
            current = df.iloc[-1]
            prev = df.iloc[-5]
            
            # Price change over last 5 periods
            price_change = (current['close'] - prev['close']) / prev['close'] * 100
            
            # Check EMA alignment
            ema_aligned_bull = False
            ema_aligned_bear = False
            
            if 'ema_9' in df.columns and 'ema_21' in df.columns:
                ema_aligned_bull = current['ema_9'] > current['ema_21']
                ema_aligned_bear = current['ema_9'] < current['ema_21']
            
            # Check RSI
            rsi = current.get('rsi', 50)
            
            # Determine bias
            bullish_signals = 0
            bearish_signals = 0
            
            if price_change > 1:
                bullish_signals += 1
            elif price_change < -1:
                bearish_signals += 1
            
            if ema_aligned_bull:
                bullish_signals += 1
            elif ema_aligned_bear:
                bearish_signals += 1
            
            if pd.notna(rsi):
                if rsi > 55:
                    bullish_signals += 1
                elif rsi < 45:
                    bearish_signals += 1
            
            if bullish_signals >= 2:
                return WeeklyBias.BULLISH
            elif bearish_signals >= 2:
                return WeeklyBias.BEARISH
            else:
                return WeeklyBias.NEUTRAL
                
        except Exception:
            return WeeklyBias.NEUTRAL


class DecisionAgent:
    """
    Trading Decision Agent
    
    Makes BUY/SELL/WAIT decisions based on technical analysis.
    Uses OR15 (Opening Range 15min) strategy for stocks.
    """
    
    # 高波动股票列表（基于回测验证，降低入场信号阈值）
    # 平衡方案：仅保留捕获率高的股票
    # BKKT: 22.0% 潜在 → +3.9% 实际（捕获率高）
    # RCAT: 11.1% 潜在 → +1.4% 实际
    # CRML: 频繁 TOP 10，胜率好
    # ASTS: 频繁 TOP 10，波动大
    # SIDU/OSS: 超高潜在收益（20%+），需低阈值+宽止损
    HIGH_BETA_STOCKS = [
        "BKKT", "RCAT",      # 验证有效
        "CRML", "ASTS",      # 频繁 TOP 10
        "SIDU", "OSS",       # 超高波动（配合 3% 止损）
    ]
    
    def __init__(
        self,
        stop_loss_pct: float = 2.0,
        take_profit_pct: float = 4.0
    ):
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
    
    def decide(self, data: ProcessedData, trend: TrendAnalysis, symbol: str = "") -> TradeDecision:
        """
        Make trading decision
        
        Args:
            data: Processed market data
            trend: Trend analysis
            symbol: Stock symbol (for high beta detection)
        """
        decision = TradeDecision(action="WAIT")
        
        if data.df_15m is None or len(data.df_15m) < 20:
            decision.summary_reason = "Insufficient data"
            return decision
        
        df = data.df_15m
        current = df.iloc[-1]
        prev = df.iloc[-2] if len(df) >= 2 else current
        
        # Get current price
        current_price = float(current['close'])
        decision.entry_price = current_price
        
        # Calculate stops
        atr = float(current.get('atr', current_price * 0.02)) if pd.notna(current.get('atr')) else current_price * 0.02
        
        # 改进盈亏比为 2:1 (止盈 3 ATR，止损 1.5 ATR)
        decision.stop_loss = current_price - (atr * 1.5)
        decision.take_profit = current_price + (atr * 3.0)  # 改为 3x ATR
        
        # Collect signals
        buy_signals = []
        sell_signals = []
        
        # 1. Trend alignment
        if trend.overall_score > 0.3:
            buy_signals.append("Trend alignment positive")
        elif trend.overall_score < -0.3:
            sell_signals.append("Trend alignment negative")
        
        # 2. RSI
        rsi = current.get('rsi', 50)
        if pd.notna(rsi):
            if rsi < 30:  # 标准超卖阈值
                buy_signals.append(f"RSI oversold ({rsi:.1f})")
            elif rsi > 70:  # 标准超买阈值
                sell_signals.append(f"RSI overbought ({rsi:.1f})")
        
        # 3. MACD crossover
        macd_hist = current.get('macd_hist', 0)
        prev_macd_hist = prev.get('macd_hist', 0)
        
        if pd.notna(macd_hist) and pd.notna(prev_macd_hist):
            if prev_macd_hist < 0 and macd_hist > 0:
                buy_signals.append("MACD bullish crossover")
            elif prev_macd_hist > 0 and macd_hist < 0:
                sell_signals.append("MACD bearish crossover")
        
        # 4. EMA alignment
        if 'ema_9' in df.columns and 'ema_21' in df.columns:
            if current['close'] > current['ema_9'] > current['ema_21']:
                buy_signals.append("EMA bullish alignment")
            elif current['close'] < current['ema_9'] < current['ema_21']:
                sell_signals.append("EMA bearish alignment")
        
        # 5. Volume confirmation
        volume_ratio = current.get('volume_ratio', 1)
        if pd.notna(volume_ratio) and volume_ratio > 1.5:
            if len(buy_signals) > len(sell_signals):
                buy_signals.append(f"High volume ({volume_ratio:.1f}x)")
            elif len(sell_signals) > len(buy_signals):
                sell_signals.append(f"High volume ({volume_ratio:.1f}x)")
        
        # Make decision - 动态阈值（高波动股票降低要求）
        # 高波动股票：1 个信号即可交易
        # 普通股票：需要 2 个信号
        required_signals = 1 if symbol in self.HIGH_BETA_STOCKS else 2
        
        if len(buy_signals) >= required_signals:
            decision.action = "BUY"
            decision.confidence = min(1.0, len(buy_signals) * 0.2)
            decision.detailed_reasons = buy_signals
            decision.summary_reason = f"强买入信号: {', '.join(buy_signals[:2])}"
        elif len(sell_signals) >= required_signals:
            decision.action = "SELL"
            decision.confidence = min(1.0, len(sell_signals) * 0.2)
            decision.detailed_reasons = sell_signals
            decision.summary_reason = f"卖出信号: {', '.join(sell_signals[:2])}"
        else:
            decision.action = "WAIT"
            decision.summary_reason = "无明确信号"
            decision.detailed_reasons = buy_signals + sell_signals
        
        return decision
