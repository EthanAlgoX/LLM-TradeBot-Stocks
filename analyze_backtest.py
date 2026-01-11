"""
回测数据分析脚本
分析最大潜在收益并提供策略优化建议
"""

import pandas as pd
import json
from collections import defaultdict

# 读取数据
session_dir = "data/backtest_results/2026-01-11_17-21-00"
df = pd.read_csv(f"{session_dir}/daily_summary.csv", encoding='utf-8-sig')

# 清理数据
df['最大潜在收益_num'] = df['最大潜在收益'].str.replace('%', '').str.replace('-', '0').astype(float)
df['收益率_num'] = df['收益率'].str.replace('%', '').str.replace('+', '').str.replace('-', '0').astype(float)

print("=" * 100)
print("📊 回测数据分析报告 - Session: 2026-01-11_17-21-00")
print("=" * 100)

# 1. 最大潜在收益 TOP 20
print("\n\n🎯 最大潜在收益 TOP 20")
print("-" * 100)
top_potential = df.nlargest(20, '最大潜在收益_num')[
    ['日期', '股票', '决策', 'OR15收盘价', '当日最高价', '最高价时间', '最大潜在收益', '是否交易', '收益率']
]
for idx, row in top_potential.iterrows():
    traded_mark = "✅" if row['是否交易'] == '是' else "❌"
    print(f"{traded_mark} {row['日期']} {row['股票']:6s} | 决策:{row['决策']:4s} | 潜在:{row['最大潜在收益']:>7s} @ {row['最高价时间']} | 实际:{row['收益率']:>7s}")

# 2. 错失的高潜力机会
print("\n\n💔 错失的高潜力机会（潜在收益 > 5% 但未交易）")
print("-" * 100)
missed = df[(df['是否交易'] == '否') & (df['最大潜在收益_num'] > 5)].sort_values('最大潜在收益_num', ascending=False)
print(f"总计: {len(missed)} 个机会\n")
for idx, row in missed.head(15).iterrows():
    print(f"📅 {row['日期']} {row['股票']:6s} | 决策:{row['决策']:4s} | 潜在:{row['最大潜在收益']:>7s} @ {row['最高价时间']} | 理由: {row['决策理由']}")

# 3. 按股票统计
print("\n\n📈 各股票统计分析")
print("-" * 100)
stock_stats = df.groupby('股票').agg({
    '最大潜在收益_num': ['mean', 'max', 'count'],
    '是否交易': lambda x: (x == '是').sum(),
    '收益率_num': lambda x: x[x != 0].mean() if (x != 0).any() else 0
}).round(2)
stock_stats.columns = ['平均潜在%', '最大潜在%', '总天数', '交易次数', '平均实际%']
stock_stats = stock_stats.sort_values('平均潜在%', ascending=False)
print(stock_stats)

# 4. 最高价时间分布
print("\n\n⏰ 最高价出现时间分布")
print("-" * 100)
df['hour'] = df['最高价时间'].str.split(':').str[0]
time_dist = df[df['最大潜在收益_num'] > 3].groupby('hour').size().sort_values(ascending=False)
print("高潜力时段（潜在收益 > 3%）:")
for hour, count in time_dist.head(10).items():
    print(f"  {hour}:00 - {count} 次")

# 5. 决策分析
print("\n\n🤔 决策分析")
print("-" * 100)
decision_analysis = df.groupby('决策').agg({
    '最大潜在收益_num': 'mean',
    '日期': 'count'
}).round(2)
decision_analysis.columns = ['平均潜在%', '次数']
print(decision_analysis)

# 6. 交易 vs 未交易对比
print("\n\n💰 交易 vs 未交易对比")
print("-" * 100)
traded = df[df['是否交易'] == '是']
not_traded = df[df['是否交易'] == '否']
print(f"已交易: {len(traded)} 次, 平均潜在收益: {traded['最大潜在收益_num'].mean():.2f}%, 平均实际收益: {traded['收益率_num'].mean():.2f}%")
print(f"未交易: {len(not_traded)} 次, 平均潜在收益: {not_traded['最大潜在收益_num'].mean():.2f}%")

print("\n" + "=" * 100)
print("✅ 分析完成")
print("=" * 100)
