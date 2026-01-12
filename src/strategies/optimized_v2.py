#!/usr/bin/env python3
"""
优化版交易策略 V2
===================

改进点:
1. 降低RSI入场门槛 (35→40)  
2. 添加布林带突破信号
3. 增强做空逻辑
4. 动态止损止盈
5. 更智能的出场条件

Author: AI Trader Team
Date: 2026-01-10
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class StrategyConfig:
    """策略配置"""
    # RSI 参数
    rsi_period: int = 14
    rsi_oversold: float = 32  # 放宽入场条件 (原25)
    rsi_overbought: float = 68  # 放宽出场条件 (原70)
    rsi_extreme_oversold: float = 25
    rsi_extreme_overbought: float = 80
    
    # EMA 参数
    ema_fast: int = 9  # 更快响应 (原12)
    ema_slow: int = 21  # 更快响应 (原26)
    ema_spread_min_pct: float = 0.18  # 趋势强度阈值 (EMA间距%)
    
    # 布林带参数
    bb_period: int = 20
    bb_std: float = 2.0
    bb_squeeze_threshold: float = 0.03  # 布林带宽度阈值 (3%)
    
    # ATR 参数
    atr_period: int = 14
    atr_sl_multiplier: float = 1.5  # 止损=ATR*1.5
    atr_tp_multiplier: float = 2.5  # 止盈=ATR*2.5
    min_atr_pct: float = 0.4  # 低波动过滤
    max_atr_pct: float = 7.5  # 高波动过滤

    # ATR 跟踪止损
    trailing_atr_multiplier: float = 1.6
    trailing_stop_min_pct: float = 1.0
    trailing_stop_max_pct: float = 4.0
    
    # 成交量
    rvol_threshold: float = 1.4  # 放宽成交量要求 (原1.5)
    rvol_breakout_threshold: float = 2.2  # 突破信号更严格

    # 做空开关
    enable_short: bool = True

    # 高周期趋势过滤
    htf_ema_fast: int = 12
    htf_ema_slow: int = 26
    htf_bias_penalty: int = 12
    htf_bias_min_confidence: int = 60


def calculate_indicators(df: pd.DataFrame, config: StrategyConfig) -> Dict:
    """计算技术指标"""
    close = df['close'].astype(float)
    high = df['high'].astype(float)
    low = df['low'].astype(float)
    volume = df['volume'].astype(float)
    
    indicators = {}
    
    # EMA
    ema_fast = close.ewm(span=config.ema_fast, adjust=False).mean()
    ema_slow = close.ewm(span=config.ema_slow, adjust=False).mean()
    indicators['ema_fast'] = ema_fast.iloc[-1]
    indicators['ema_slow'] = ema_slow.iloc[-1]
    indicators['ema_fast_prev'] = ema_fast.iloc[-2]
    indicators['ema_slow_prev'] = ema_slow.iloc[-2]
    
    # EMA趋势
    indicators['is_uptrend'] = indicators['ema_fast'] > indicators['ema_slow']
    indicators['golden_cross'] = (indicators['ema_fast'] > indicators['ema_slow'] and 
                                   indicators['ema_fast_prev'] <= indicators['ema_slow_prev'])
    indicators['death_cross'] = (indicators['ema_fast'] < indicators['ema_slow'] and 
                                  indicators['ema_fast_prev'] >= indicators['ema_slow_prev'])
    ema_spread_pct = abs(indicators['ema_fast'] - indicators['ema_slow']) / close.iloc[-1] * 100
    indicators['ema_spread_pct'] = ema_spread_pct
    indicators['is_trending'] = ema_spread_pct >= config.ema_spread_min_pct
    
    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(window=config.rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=config.rsi_period).mean()
    rs = gain / loss.replace(0, 1e-10)
    rsi = 100 - (100 / (1 + rs))
    indicators['rsi'] = rsi.iloc[-1]
    indicators['rsi_prev'] = rsi.iloc[-2]
    
    # MACD
    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema_12 - ema_26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    macd_hist = macd_line - signal_line
    indicators['macd_hist'] = macd_hist.iloc[-1]
    indicators['macd_hist_prev'] = macd_hist.iloc[-2]
    indicators['macd_momentum'] = indicators['macd_hist'] > indicators['macd_hist_prev']
    indicators['macd_positive'] = indicators['macd_hist'] > 0
    
    # 布林带
    bb_mid = close.rolling(window=config.bb_period).mean()
    bb_std = close.rolling(window=config.bb_period).std()
    bb_upper = bb_mid + config.bb_std * bb_std
    bb_lower = bb_mid - config.bb_std * bb_std
    indicators['bb_upper'] = bb_upper.iloc[-1]
    indicators['bb_lower'] = bb_lower.iloc[-1]
    indicators['bb_mid'] = bb_mid.iloc[-1]
    bb_width = bb_upper.iloc[-1] - bb_lower.iloc[-1]
    bb_mid_value = bb_mid.iloc[-1]
    indicators['bb_width'] = bb_width / bb_mid_value if bb_mid_value else 0.0
    indicators['bb_position'] = (close.iloc[-1] - bb_lower.iloc[-1]) / bb_width if bb_width else 0.5
    indicators['bb_squeeze'] = indicators['bb_width'] < config.bb_squeeze_threshold
    
    # ATR
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=config.atr_period).mean()
    indicators['atr'] = atr.iloc[-1]
    indicators['atr_pct'] = (atr.iloc[-1] / close.iloc[-1]) * 100
    
    # 成交量
    avg_volume = volume.rolling(window=20).mean().iloc[-1]
    current_volume = volume.iloc[-1]
    indicators['rvol'] = current_volume / avg_volume if avg_volume > 0 else 1.0
    
    # 价格
    indicators['price'] = close.iloc[-1]
    indicators['price_prev'] = close.iloc[-2]
    
    return indicators


def optimized_strategy_v2(
    snapshot,
    portfolio,
    current_price: float,
    config,  # BacktestConfig
    strategy_config: Optional[StrategyConfig] = None
) -> Dict:
    """
    优化版策略 V2
    
    核心改进:
    1. 多信号融合 (RSI + EMA + MACD + 布林带)
    2. 动态止损止盈 (基于ATR)
    3. 增强做空逻辑
    4. 更灵活的入场条件
    """
    if strategy_config is None:
        strategy_config = StrategyConfig()
    
    # 获取数据
    df = snapshot.stable_5m.copy()
    
    if len(df) < 50:
        return {'action': 'hold', 'confidence': 0.0, 'reason': 'insufficient_data'}
    
    # 计算指标
    ind = calculate_indicators(df, strategy_config)

    # 高周期趋势过滤 (1h)
    htf_bias = None
    htf_df = getattr(snapshot, 'stable_1h', None)
    if isinstance(htf_df, pd.DataFrame) and 'close' in htf_df.columns:
        if len(htf_df) >= max(strategy_config.htf_ema_slow + 2, 30):
            close_1h = htf_df['close'].astype(float)
            ema_fast_1h = close_1h.ewm(span=strategy_config.htf_ema_fast, adjust=False).mean()
            ema_slow_1h = close_1h.ewm(span=strategy_config.htf_ema_slow, adjust=False).mean()
            if np.isfinite(ema_fast_1h.iloc[-1]) and np.isfinite(ema_slow_1h.iloc[-1]):
                htf_bias = 'up' if ema_fast_1h.iloc[-1] > ema_slow_1h.iloc[-1] else 'down'

    allow_long = htf_bias != 'down'
    allow_short = htf_bias != 'up'

    def apply_bias_confidence(base_conf: int, allow_bias: bool, allow_countertrend: bool = False):
        if allow_bias:
            return base_conf
        if not allow_countertrend:
            return None
        return max(base_conf - strategy_config.htf_bias_penalty, strategy_config.htf_bias_min_confidence)
    
    # 持仓状态
    symbol = config.symbol
    has_position = symbol in portfolio.positions
    
    # 动态止损止盈参数
    atr_sl = ind['atr'] * strategy_config.atr_sl_multiplier
    atr_tp = ind['atr'] * strategy_config.atr_tp_multiplier
    trailing_stop_pct = None
    if np.isfinite(ind['atr_pct']) and ind['atr_pct'] > 0:
        trailing_stop_pct = float(np.clip(
            ind['atr_pct'] * strategy_config.trailing_atr_multiplier,
            strategy_config.trailing_stop_min_pct,
            strategy_config.trailing_stop_max_pct
        ))
    
    trade_params = {
        'stop_loss_pct': (atr_sl / current_price) * 100,
        'take_profit_pct': (atr_tp / current_price) * 100,
        'trailing_stop_pct': trailing_stop_pct,
    }
    
    # ========== 入场信号 ==========
    
    if not has_position:
        # 波动过滤
        if not np.isfinite(ind['atr_pct']):
            return {'action': 'hold', 'confidence': 0.0, 'reason': 'atr_unavailable'}
        if ind['atr_pct'] < strategy_config.min_atr_pct:
            return {'action': 'hold', 'confidence': 10, 'reason': f'low_vol_atr{ind["atr_pct"]:.2f}%'}
        if ind['atr_pct'] > strategy_config.max_atr_pct:
            return {'action': 'hold', 'confidence': 10, 'reason': f'high_vol_atr{ind["atr_pct"]:.2f}%'}

        # 🟢 做多信号
        long_signals = []
        in_squeeze = ind['bb_squeeze']
        breakout_rvol = ind['rvol'] > strategy_config.rvol_breakout_threshold

        # 信号0: 低波动挤压后的突破
        if in_squeeze and ind['price'] > ind['bb_upper'] and breakout_rvol and ind['macd_momentum']:
            confidence = apply_bias_confidence(80, allow_long, allow_countertrend=True)
            if confidence:
                long_signals.append(('bb_squeeze_breakout', confidence))
        
        # 信号1: RSI超卖 + 上升趋势
        if ind['rsi'] < strategy_config.rsi_oversold and ind['is_uptrend'] and ind['is_trending'] and not in_squeeze:
            confidence = apply_bias_confidence(75, allow_long)
            if confidence:
                long_signals.append(('rsi_oversold_uptrend', confidence))
        
        # 信号2: RSI极度超卖 (任何趋势)
        if ind['rsi'] < strategy_config.rsi_extreme_oversold:
            confidence = apply_bias_confidence(85, allow_long, allow_countertrend=True)
            if confidence:
                long_signals.append(('rsi_extreme_oversold', confidence))
        
        # 信号3: 金叉 + MACD确认
        if ind['golden_cross'] and ind['macd_positive'] and ind['is_trending'] and not in_squeeze:
            confidence = apply_bias_confidence(80, allow_long)
            if confidence:
                long_signals.append(('golden_cross_macd+', confidence))
        
        # 信号4: 布林带下轨突破 + RSI不超买
        if ind['bb_position'] < 0.1 and ind['rsi'] < 50:
            confidence = apply_bias_confidence(70, allow_long, allow_countertrend=breakout_rvol)
            if confidence:
                long_signals.append(('bb_lower_breakout', confidence))
        
        # 信号5: RSI背离反转
        if ind['rsi'] < 40 and ind['rsi'] > ind['rsi_prev'] and ind['macd_momentum']:
            confidence = apply_bias_confidence(65, allow_long, allow_countertrend=True)
            if confidence:
                long_signals.append(('rsi_reversal', confidence))
        
        # 选择最强信号
        if long_signals:
            best_signal = max(long_signals, key=lambda x: x[1])
            confidence = best_signal[1]
            
            # 成交量加权
            if ind['rvol'] > strategy_config.rvol_threshold:
                confidence = min(confidence + 5, 95)
            
            return {
                'action': 'long',
                'confidence': confidence,
                'reason': f'long_{best_signal[0]}_rsi{ind["rsi"]:.0f}',
                'trade_params': trade_params,
                'atr_pct': ind['atr_pct']
            }
        
        # 🔴 做空信号 (如果启用)
        if strategy_config.enable_short:
            short_signals = []
            # 信号0: 低波动挤压后的向下突破
            if in_squeeze and ind['price'] < ind['bb_lower'] and breakout_rvol and not ind['macd_positive']:
                confidence = apply_bias_confidence(80, allow_short, allow_countertrend=True)
                if confidence:
                    short_signals.append(('bb_squeeze_breakout', confidence))
            
            # 信号1: RSI超买 + 下降趋势
            if ind['rsi'] > strategy_config.rsi_overbought and not ind['is_uptrend'] and ind['is_trending'] and not in_squeeze:
                confidence = apply_bias_confidence(75, allow_short)
                if confidence:
                    short_signals.append(('rsi_overbought_downtrend', confidence))
            
            # 信号2: RSI极度超买
            if ind['rsi'] > strategy_config.rsi_extreme_overbought:
                confidence = apply_bias_confidence(80, allow_short, allow_countertrend=True)
                if confidence:
                    short_signals.append(('rsi_extreme_overbought', confidence))
            
            # 信号3: 死叉 + MACD确认
            if ind['death_cross'] and not ind['macd_positive'] and ind['is_trending'] and not in_squeeze:
                confidence = apply_bias_confidence(80, allow_short)
                if confidence:
                    short_signals.append(('death_cross_macd-', confidence))
            
            # 信号4: 布林带上轨突破 + RSI超买
            if ind['bb_position'] > 0.95 and ind['rsi'] > 60:
                confidence = apply_bias_confidence(70, allow_short, allow_countertrend=breakout_rvol)
                if confidence:
                    short_signals.append(('bb_upper_breakout', confidence))
            
            # 选择最强信号
            if short_signals:
                best_signal = max(short_signals, key=lambda x: x[1])
                confidence = best_signal[1]
                
                if ind['rvol'] > strategy_config.rvol_threshold:
                    confidence = min(confidence + 5, 95)
                
                return {
                    'action': 'short',
                    'confidence': confidence,
                    'reason': f'short_{best_signal[0]}_rsi{ind["rsi"]:.0f}',
                    'trade_params': trade_params,
                    'atr_pct': ind['atr_pct']
                }
    
    # ========== 持仓管理 ==========
    
    if has_position:
        from src.backtest.portfolio import Side
        
        position = portfolio.positions[symbol]
        current_side = position.side
        entry_price = position.entry_price
        
        if current_side == Side.LONG:
            pnl_pct = (current_price / entry_price - 1) * 100
        else:
            pnl_pct = (entry_price / current_price - 1) * 100
        
        # 🎯 多头出场
        if current_side == Side.LONG:
            # 条件1: RSI超买 + 动量减弱
            if ind['rsi'] > strategy_config.rsi_overbought and not ind['macd_momentum']:
                return {'action': 'close', 'confidence': 75, 'reason': f'tp_rsi{ind["rsi"]:.0f}_macd_weak'}
            
            # 条件2: RSI极度超买
            if ind['rsi'] > strategy_config.rsi_extreme_overbought:
                return {'action': 'close', 'confidence': 85, 'reason': f'tp_rsi_extreme_{ind["rsi"]:.0f}'}
            
            # 条件3: 死叉 + 亏损
            if ind['death_cross'] and pnl_pct < 0:
                return {'action': 'close', 'confidence': 70, 'reason': f'sl_death_cross_pnl{pnl_pct:.1f}%'}
            
            # 条件4: 布林带上轨获利了结
            if ind['bb_position'] > 0.95 and pnl_pct > 0.5:
                return {'action': 'close', 'confidence': 65, 'reason': f'tp_bb_upper_pnl{pnl_pct:.1f}%'}
        
        # 🎯 空头出场
        elif current_side == Side.SHORT:
            # 条件1: RSI超卖
            if ind['rsi'] < strategy_config.rsi_oversold:
                return {'action': 'close', 'confidence': 75, 'reason': f'tp_short_rsi{ind["rsi"]:.0f}'}
            
            # 条件2: 金叉
            if ind['golden_cross']:
                return {'action': 'close', 'confidence': 70, 'reason': 'sl_golden_cross'}
            
            # 条件3: 布林带下轨获利了结
            if ind['bb_position'] < 0.05 and pnl_pct > 0.5:
                return {'action': 'close', 'confidence': 65, 'reason': f'tp_bb_lower_pnl{pnl_pct:.1f}%'}
        
        # 继续持有
        return {'action': 'hold', 'confidence': 50, 'reason': f'holding_pnl{pnl_pct:+.1f}%'}
    
    # 无信号
    return {'action': 'hold', 'confidence': 30, 'reason': 'no_signal'}


# 导出策略函数
async def strategy_v2_wrapper(snapshot, portfolio, current_price: float, config) -> Dict:
    """异步包装器"""
    return optimized_strategy_v2(snapshot, portfolio, current_price, config)
