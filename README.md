# 🤖 LLM-TradeBot-Stocks

[![English](https://img.shields.io/badge/Language-English-blue.svg)](README.md) [![简体中文](https://img.shields.io/badge/Language-简体中文-green.svg)](README_CN.md)

**Intelligent US Stock Intraday Trading Backtest System** based on simplified multi-agent framework with technical analysis and OR15 (Opening Range 15-minute) strategy.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-AGPL%20v3.0-blue.svg)](LICENSE)
[![Framework](https://img.shields.io/badge/Strategy-OR15%20%2B%20Multi--Agent-gold.svg)](https://github.com/EthanAlgoX/LLM-TradeBot-Stocks)

---

## ✨ Key Features

- 📊 **US Stock Backtesting**: Professional-grade backtesting system for US equities using Alpaca API
- 🤖 **3-Agent Framework**: Lightweight multi-agent architecture for technical analysis
  - **DataProcessorAgent**: Multi-timeframe data processing (Weekly/Daily/15m)
  - **MultiPeriodAgent**: Trend analysis across multiple periods
  - **DecisionAgent**: Trading decision engine with dynamic signal thresholds
- 📈 **OR15 Strategy**: Opening Range 15-minute breakout strategy
- 🎯 **Smart Optimization**:
  - High-beta stock detection with lower signal thresholds
  - Dynamic take-profit based on time of day
  - Trailing stop loss for profit protection
- 📁 **Comprehensive Data Recording**:
  - All stocks recorded (including WAIT decisions)
  - Per-day JSON files with complete trade details
  - Maximum potential profit tracking with timestamp
- 🔄 **Auto Session Management**: Keeps only 5 most recent backtest sessions
- 📊 **91-Stock Watchlist**: Curated 2026 stock pool with sector categorization

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Alpaca API keys (for data fetching)

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd LLM-TradeBot-Stocks

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env and add your Alpaca API keys
```

### Run Backtest

```bash
# Backtest all 91 stocks (default), last 30 days
python backtest_daily.py --days 30

# Backtest high-momentum stocks only (7 stocks)
python backtest_daily.py --preset momentum --days 30

# Backtest specific stocks
python backtest_daily.py --symbols AAPL,TSLA,NVDA --days 60

# Quiet mode (less verbose)
python backtest_daily.py --days 30 --quiet
```

---

## 🏗️ Architecture

### 3-Agent Framework

```
┌─────────────────────────────────────────────────────────┐
│                  DataProcessorAgent                     │
│  • Fetches multi-timeframe data (Weekly/Daily/15m)     │
│  • Calculates technical indicators (EMA, RSI, MACD)    │
│  • Provides ProcessedData to other agents              │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│                  MultiPeriodAgent                       │
│  • Analyzes trends across multiple timeframes          │
│  • Generates TrendAnalysis with scores                 │
│  • Detects weekly bias (Bullish/Bearish/Neutral)       │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│                   DecisionAgent                         │
│  • Collects buy/sell signals from indicators           │
│  • Dynamic signal threshold (1 for high-beta, 2 for normal) │
│  • Generates TradeDecision (BUY/SELL/WAIT)             │
└─────────────────────────────────────────────────────────┘
```

### OR15 Strategy

**Opening Range 15-minute (OR15)** strategy:

1. **Entry**: 15 minutes after market open (9:45 AM ET)
2. **Monitoring**: Track 15-minute bars for stop-loss/take-profit
3. **Exit**: Forced close before market close (4:00 PM ET)

**Optimizations**:

- **High-Beta Stocks** (BKKT, RCAT): Lower signal threshold for more opportunities
- **Dynamic Take-Profit**: 4% (early), 5% (mid-day), 6% (late)
- **Trailing Stop**: Activates at 2% profit, trails at 1.5%

---

## 📊 Backtest Output

### File Structure

```
data/backtest_results/
└── 2026-01-11_17-21-00/          # Session timestamp
    ├── daily_summary.csv          # All stocks, all days
    ├── trades_summary.csv         # Trade details
    ├── traded_stocks_summary.json # Per-stock statistics
    └── 2026-01-06/                # Per-day folder
        ├── AAPL.json              # All stocks (including WAIT)
        ├── TSLA.json
        └── ...
```

### Daily Record Fields

Each stock's daily JSON includes:

- `action`: BUY / WAIT
- `decision_reason`: Why the decision was made
- `or15_high`, `or15_low`, `or15_close`: Opening range data
- `day_high_after_or15`: Highest price after OR15
- `day_high_time`: When the high occurred (ET)
- `max_potential_pct`: Maximum possible profit
- `traded`: Whether a trade was executed
- `entry_price`, `exit_price`, `pnl_pct`: Trade results

---

## 📈 Stock Watchlist

The system includes a curated **91-stock watchlist** (`src/config/watchlist_2026.py`) with:

- **HIGH_MOMENTUM** (7 stocks): BKKT, RCAT, NVTS, SNDX, EOSE, AEHR, APLD
- **AI_RELATED** (30+ stocks): AI and data-related companies
- **ALL_TICKERS** (91 stocks): Complete watchlist with sector categorization

### Presets

```bash
--preset momentum  # 7 high-momentum stocks
--preset ai        # 10 AI-related stocks  
--preset all       # All 91 stocks (default)
```

---

## 🎯 Strategy Optimization Results

Based on backtest analysis (30 days):

| Metric | Before | After Optimization | Improvement |
|--------|--------|-------------------|-------------|
| Win Rate | 37.0% | **44.2%** | +7.2% |
| Profitable Trades | 10 | **19** | +90% |
| Total Trades | 27 | 43 | +59% |

**Key Improvements**:

- ✅ High-beta stock optimization (BKKT: 80% win rate on 10-day test)
- ✅ Dynamic take-profit captures more late-day moves
- ✅ Trailing stop protects profits (+1-2% instead of -2%)

---

## 🛠️ Advanced Usage

### Custom Stock Selection

```python
# Edit src/config/watchlist_2026.py
CUSTOM_LIST = ["AAPL", "MSFT", "GOOGL"]

# Run backtest
python backtest_daily.py --symbols AAPL,MSFT,GOOGL --days 30
```

### Analyze Results

```python
# Use the analysis script
python analyze_backtest.py

# View traded stocks summary
cat data/backtest_results/latest/traded_stocks_summary.json
```

---

## 📁 Project Structure

```
LLM-TradeBot-Stocks/
├── backtest_daily.py          # Main backtest script
├── analyze_backtest.py        # Backtest analysis tool
├── src/
│   ├── agents/
│   │   └── simple_agents.py   # 3-Agent framework
│   ├── api/
│   │   ├── alpaca_client.py   # Alpaca data client
│   │   └── market_client.py   # Unified market interface
│   ├── config/
│   │   └── watchlist_2026.py  # Stock watchlist
│   └── utils/
│       ├── data_cache.py      # Data caching
│       └── data_manager.py    # Data storage manager
├── data/
│   ├── raw_data/              # Raw OHLCV data
│   ├── backtest_results/      # Backtest sessions (5 most recent)
│   └── oi_history/            # Open interest data
└── requirements.txt
```

---

## 🔧 Configuration

### Environment Variables (.env)

```bash
# Alpaca API (required for data fetching)
ALPACA_API_KEY=your_api_key
ALPACA_SECRET_KEY=your_secret_key
ALPACA_PAPER=true  # Use paper trading endpoint
```

### Strategy Parameters

Edit `backtest_daily.py` to customize:

- `SLIPPAGE_PCT`: Transaction cost simulation (default: 0.1%)
- `TRAILING_ACTIVATION_PCT`: Profit threshold for trailing stop (default: 2%)
- `TRAILING_DISTANCE_PCT`: Trailing stop distance (default: 1.5%)

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [README.md](README.md) | This file |
| [LICENSE](LICENSE) | AGPL-3.0 License |
| [QUICKSTART.md](QUICKSTART.md) | Quick start guide |
| [.env.example](.env.example) | Environment variables template |

---

## 🤝 Contributing

Issues and Pull Requests are welcome!

---

## 📜 License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**.

### What This Means

- ✅ **Free to Use**: You can use this software for any purpose, including commercial use
- ✅ **Free to Modify**: You can modify the source code to suit your needs
- ✅ **Free to Distribute**: You can share the software with others
- ⚠️ **Network Use = Distribution**: If you run this software on a server and let others interact with it over a network, you must provide them with the source code
- ⚠️ **Share Modifications**: Any modifications you make must also be licensed under AGPL-3.0
- ⚠️ **Preserve Copyright**: You must keep all copyright notices intact

### Why AGPL-3.0?

We chose AGPL-3.0 to ensure that improvements to this trading bot remain open source and benefit the entire community, even when deployed as a service. This prevents proprietary forks from keeping improvements private.

For full license text, see the [LICENSE](LICENSE) file.

---

**Empowered by AI, Focused on Precision, Starting a New Era of Intelligent Quant!** 🚀
