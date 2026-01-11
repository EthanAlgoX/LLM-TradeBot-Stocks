#!/usr/bin/env python3
"""
批量读取 raw_data 数据
=======================

一次性读取最近 N 天的所有股票 15m K 线数据

Usage:
    python load_raw_data.py --days 7
    python load_raw_data.py --days 7 --output data/combined_data.json
"""

import os
import json
import argparse
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Any
import pandas as pd


def get_trading_days(raw_data_path: str, n_days: int) -> List[str]:
    """获取最近 N 个交易日"""
    dates = sorted([
        d for d in os.listdir(raw_data_path)
        if os.path.isdir(os.path.join(raw_data_path, d)) and d.startswith('202')
    ], reverse=True)
    return dates[:n_days]


def load_all_raw_data(
    raw_data_path: str = "data/raw_data",
    n_days: int = 7
) -> Dict[str, Dict[str, Any]]:
    """
    批量读取 raw_data
    
    Returns:
        {
            "2026-01-09": {
                "AAPL": {"bars": [...], "count": 26},
                "TSLA": {"bars": [...], "count": 26},
                ...
            },
            ...
        }
    """
    trading_days = get_trading_days(raw_data_path, n_days)
    
    print(f"📊 读取最近 {len(trading_days)} 个交易日的数据...")
    print(f"   日期范围: {trading_days[-1]} ~ {trading_days[0]}")
    print(f"   筛选时间: 09:30 - 16:00 (ET)")
    
    all_data = {}
    total_files = 0
    total_bars = 0
    
    # ET 时区
    from zoneinfo import ZoneInfo
    ET = ZoneInfo("America/New_York")
    MARKET_OPEN = 9 * 60 + 30  # 9:30 in minutes
    MARKET_CLOSE = 16 * 60     # 16:00 in minutes
    
    for day_str in trading_days:
        day_path = os.path.join(raw_data_path, day_str)
        day_data = {}
        
        files = [f for f in os.listdir(day_path) if f.endswith('_15m.json')]
        
        for filename in files:
            symbol = filename.replace('_15m.json', '')
            filepath = os.path.join(day_path, filename)
            
            try:
                with open(filepath, 'r') as f:
                    file_content = json.load(f)
                    raw_bars = file_content if isinstance(file_content, list) else file_content.get('bars', [])
                    
                    filtered_bars = []
                    for bar in raw_bars:
                        # 获取时间戳 string
                        ts_str = bar.get('timestamp') or bar.get('t')
                        if not ts_str:
                            continue
                            
                        # 解析时间并转换时区
                        ts = pd.to_datetime(ts_str)
                        if ts.tz is None:
                            # 存储的时间已经是 ET，直接本地化为 ET
                            ts_et = ts.tz_localize(ET)
                        else:
                            ts_et = ts.tz_convert(ET)
                        
                        # 计算分钟数 (from midnight)
                        minutes = ts_et.hour * 60 + ts_et.minute
                        
                        # 筛选 09:30 <= time < 16:00 (15:45 bar covers 15:45-16:00)
                        if MARKET_OPEN <= minutes < MARKET_CLOSE:
                            # 统一格式化时间
                            bar_copy = bar.copy()
                            bar_copy['timestamp'] = ts_et.strftime('%Y-%m-%d %H:%M:%S')
                            filtered_bars.append(bar_copy)
                    
                    if filtered_bars:
                        day_data[symbol] = {
                            "bars": filtered_bars,
                            "count": len(filtered_bars)
                        }
                        total_bars += len(filtered_bars)
                        total_files += 1
            except Exception as e:
                print(f"  ⚠️ 读取失败: {filepath}: {e}")
        
        all_data[day_str] = day_data
        print(f"  ✅ {day_str}: {len(day_data)} 只股票 (ET 09:30-16:00)")
    
    print(f"\n📈 读取完成!")
    print(f"   文件数: {total_files}")
    print(f"   K线总数: {total_bars:,}")
    print(f"   股票数: {len(set(s for d in all_data.values() for s in d.keys()))}")
    
    return all_data


def to_dataframe(all_data: Dict) -> pd.DataFrame:
    """转换为 DataFrame 格式"""
    records = []
    
    for day_str, day_data in all_data.items():
        for symbol, data in day_data.items():
            for bar in data['bars']:
                records.append({
                    'date': day_str,
                    'symbol': symbol,
                    'timestamp': bar.get('timestamp'),
                    'open': bar.get('open'),
                    'high': bar.get('high'),
                    'low': bar.get('low'),
                    'close': bar.get('close'),
                    'volume': bar.get('volume')
                })
    
    df = pd.DataFrame(records)
    return df


def main():
    parser = argparse.ArgumentParser(description="批量读取 raw_data")
    parser.add_argument("--days", type=int, default=7, help="读取最近 N 天数据")
    parser.add_argument("--output", type=str, help="输出 JSON 文件路径")
    parser.add_argument("--csv", type=str, help="输出 CSV 文件路径")
    
    args = parser.parse_args()
    
    # 读取数据
    all_data = load_all_raw_data(n_days=args.days)
    
    # 输出 JSON
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(all_data, f, indent=2)
        print(f"\n💾 已保存: {args.output}")
    
    # 输出 CSV
    if args.csv:
        df = to_dataframe(all_data)
        df.to_csv(args.csv, index=False)
        print(f"💾 已保存: {args.csv}")
    
    # 返回统计
    print(f"\n📊 数据统计:")
    for day_str, day_data in sorted(all_data.items()):
        total_bars = sum(d['count'] for d in day_data.values())
        print(f"   {day_str}: {len(day_data)} 股票, {total_bars} K线")


if __name__ == "__main__":
    main()
