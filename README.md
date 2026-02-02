# Algorithmic Trading System - ML-Enhanced Multi-Stock Portfolio

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Validated: 2025](https://img.shields.io/badge/Validated-2025-brightgreen.svg)](PRODUCTION_SYSTEM.md)

A sophisticated algorithmic trading system that combines machine learning, regime detection, and multi-stock portfolio management. **Phase 6A validated on 2025 out-of-sample data: 18.70% annual return** with realistic trading costs included.

## 🚀 Quick Start

```bash
# Clone repository
git clone https://github.com/BLx-Ankush/Trading-ML.git
cd Trading-ML

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run demo (no broker credentials needed)
python quick_start_demo.py
```

## 📈 Latest Performance (Phase 6A - 2025 Validation)

**Out-of-Sample Results (2025 unseen data):**
- **Net Return:** 18.41% (Annualized: 18.70%)
- **Win Rate:** 61.76% (21 wins, 13 losses)
- **Sharpe Ratio:** 2.17
- **Max Drawdown:** 2.71%
- **Profit Factor:** 2.69
- **Total Trades:** 34
- **Deployment Status:** ✅ All 5 criteria PASSED

## 🎯 Historical Performance (2020-2024 Training Data)

- **234.39% Total Return** over 5 years (2020-2024)
- **3.85% Monthly Return** (46% annualized)
- **52.16% Win Rate** across 255 trades
- **4.19 Trades/Month** average frequency
- **15-Stock Portfolio** with automatic diversification
- **Sharpe Ratio: 0.49** (risk-adjusted performance)

## 📊 Performance Comparison

| Metric | Single Stock | Multi-Stock Portfolio | Improvement |
|--------|--------------|----------------------|-------------|
| **Total Return** | 6.59% | **234.39%** | **+3,457%** |
| **Monthly Return** | 0.11% | **3.85%** | **35x** |
| **Total Trades** | 23 | **255** | **11x** |
| **Monthly Trades** | 0.38 | **4.19** | **11x** |
| **Win Rate** | 60.87% | 52.16% | -8.7% |

## 🏗️ System Architecture

### Three-Layer Strategy Framework

```
┌─────────────────────────────────────────────────────────────┐
│                    PORTFOLIO LAYER                           │
│  • Multi-stock management (15 NSE stocks)                   │
│  • Capital allocation (Rs. 2 lakhs)                         │
│  • Position limits (max 5 concurrent)                       │
│  • Risk management (1% per trade, 5% portfolio max)        │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│              LAYER 1: REGIME DETECTION (HMM)                │
│  • 3-state Hidden Markov Model                              │
│  • Trending (70%), Ranging (26.5%), High Volatility (3.5%) │
│  • Context-aware signal generation                          │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│         LAYER 2: FUZZY LOGIC CANDIDATE GENERATION           │
│  • Trending signals: RSI, ADX, EMA trend                   │
│  • Ranging signals: RSI, Bollinger Bands, mean reversion   │
│  • Generates 200-500 candidates per stock                   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│           LAYER 3: ML GATEKEEPER (LightGBM)                 │
│  • Binary classifier with 27 engineered features            │
│  • AUC: 0.8678 (excellent discrimination)                   │
│  • Threshold: 0.30 (60% precision on validation)            │
│  • Filters candidates to high-probability winners           │
└─────────────────────────────────────────────────────────────┘
```

## 🔬 Technical Components

### 1. **Regime Detection** (`src/models/hmm_regime.py`)
- **Algorithm**: 3-state Hidden Markov Model
- **Input**: Returns, volatility, volume
- **Output**: Market state classification
- **Purpose**: Context-aware trade filtering

### 2. **Feature Engineering** (`src/ml/feature_engineer.py`)
- **27 Features** across 5 categories:
  - **Momentum** (10): RSI, MACD, momentum indicators
  - **Mean Reversion** (6): Bollinger Bands, distance from highs/lows
  - **Volatility** (4): ATR, volatility expansion/contraction
  - **Volume** (3): Volume ratios, spikes, trends
  - **Regime** (4): Regime state, duration, transitions

### 3. **Machine Learning Model** (`src/ml/lightgbm_model.py`)
- **Algorithm**: LightGBM Gradient Boosting
- **Training**: Time-series cross-validation
- **Performance**: 
  - AUC: 0.8678
  - Validation Precision: 60%+
  - Baseline Win Rate: 23.6% → Final: 60.87%

### 4. **Risk Management** (`src/risk/`)
- **Position Sizing**: ATR-based, 1% risk per trade
- **Stop Loss**: 2 × ATR below entry
- **Take Profit**: 4 × ATR above entry (2:1 R:R)
- **Portfolio Risk**: Maximum 5% total exposure
- **Position Limits**: Max 5 concurrent trades

### 5. **Portfolio Engine** (`src/backtesting/portfolio_engine.py`)
- **Multi-stock coordination**: Simultaneous trading across 15 stocks
- **Capital allocation**: Dynamic position sizing
- **Diversification**: Sector-balanced portfolio
- **Performance tracking**: Per-symbol and portfolio-level metrics

## 📁 Project Structure

```
Trading ALGO/
│
├── src/
│   ├── data/
│   │   ├── data_loader.py          # Yahoo Finance data fetching
│   │   └── data_processor.py       # Data cleaning and validation
│   │
│   ├── features/
│   │   └── indicators.py           # Technical indicators (50+ indicators)
│   │
│   ├── models/
│   │   └── hmm_regime.py           # Hidden Markov Model for regime detection
│   │
│   ├── ml/
│   │   ├── label_creator.py        # Forward-looking label generation (2:1 R:R)
│   │   ├── feature_engineer.py     # 27 ML features creation
│   │   └── lightgbm_model.py       # Gradient boosting classifier
│   │
│   ├── strategy/
│   │   ├── strategy_selector.py    # Fuzzy logic candidate generation
│   │   └── ml_strategy_selector.py # ML-enhanced entry signals
│   │
│   ├── risk/
│   │   ├── position_sizing.py      # ATR-based position sizing
│   │   └── risk_manager.py         # Portfolio risk management
│   │
│   ├── backtesting/
│   │   ├── engine.py               # Single-stock backtest engine
│   │   └── portfolio_engine.py     # Multi-stock portfolio engine
│   │
│   └── utils/
│       └── logger.py               # Logging configuration
│
├── data/
│   ├── models/
│   │   ├── hmm_regime_model.pkl    # Trained HMM model
│   │   └── lightgbm_entry_model.txt # Trained LightGBM model
│   │
│   └── raw/                        # Cached stock data
│
├── test_phase4_portfolio.py       # Main portfolio backtest script
├── test_phase3_backtest.py        # Single-stock backtest script
│
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

## 🚀 Installation & Setup

### Prerequisites
- Python 3.11+
- Virtual environment (recommended)

### Installation

```bash
# Clone the repository
cd "D:\Trading ALGO"

# Create virtual environment (if not exists)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install pandas numpy scipy scikit-learn yfinance matplotlib seaborn tqdm arch statsmodels python-dotenv pyyaml pandas-ta lightgbm hmmlearn
```

## 📖 Usage

### 1. **Run Portfolio Backtest** (Recommended)

```bash
python test_phase4_portfolio.py
```

**Output:**
- Overall portfolio performance metrics
- Per-symbol breakdown
- Monthly return analysis
- Comparison vs single-stock strategy

### 2. **Run Single-Stock Backtest**

```bash
python test_phase3_backtest.py
```

### 3. **Custom Configuration**

```python
from test_phase4_portfolio import run_portfolio_backtest

# Customize parameters
portfolio = run_portfolio_backtest(
    stocks=['RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS'],  # Your stock universe
    start_date="2020-01-01",
    end_date="2024-12-31",
    initial_capital=200000,      # Rs. 2 lakhs
    max_positions=5              # Max concurrent trades
)
```

## 🎓 Development Journey

### Phase 1: Baseline System
- **Random entry strategy**: 9.10% return, 32 trades
- Established performance baseline
- Validated execution engine

### Phase 2: Regime Detection
- **HMM implementation**: 3-state model
- Rule-based filtering: **Failed** (precision-recall valley)
- Key learning: Need ML for better discrimination

### Phase 3: Machine Learning Integration
- **Phase 3.1-3.3**: Label creation, feature engineering, LightGBM training
  - AUC: 0.8678 (excellent)
  - 27 features engineered
  
- **Phase 3.4**: Initial integration: **Failed** (2-10 trades)
  - Problem: Over-filtering by fuzzy logic
  
- **Phase 3.5**: High-recall reset: **Success**
  - Loosened fuzzy thresholds
  - Result: 23 trades, 60.87% win rate, 6.59% return
  
- **Phase 3.6-3.7**: R:R ratio experiments
  - Tested 1.5:1 and 1.75:1 R:R ratios
  - Result: **Failed** - Lower R:R = Worse ML discrimination
  
- **Phase 3.8**: Regime-adaptive thresholds
  - Trending: 0.20, Ranging: 0.28
  - Result: **Failed** - Added trades but reduced win rate

### Phase 4: Multi-Stock Portfolio (BREAKTHROUGH)
- **Portfolio approach**: 15 NSE stocks simultaneously
- **Result**: **234.39% return** (35x improvement)
- **Key insight**: Diversification multiplies opportunities without sacrificing quality

## 📈 Stock Universe

**15 NSE Stocks** (Sector-Diversified):

| Sector | Stocks |
|--------|--------|
| **Banking** | HDFCBANK, ICICIBANK, SBIN, KOTAKBANK, AXISBANK |
| **IT Services** | TCS, INFY, HCLTECH |
| **Oil & Gas** | RELIANCE |
| **FMCG** | HINDUNILVR, ITC |
| **Finance** | BAJFINANCE |
| **Infrastructure** | LT |
| **Telecom** | BHARTIARTL |
| **Automobile** | MARUTI |

## ⚙️ Configuration

### Risk Parameters (Adjustable)

```python
# In portfolio_engine.py
initial_capital = 200000        # Rs. 2 lakhs
max_positions = 5               # Max concurrent trades
risk_per_trade = 0.01          # 1% risk per trade
max_portfolio_risk = 0.05      # 5% total portfolio risk

# In strategy
risk_reward_ratio = 2.0        # 2:1 R:R (stop: 2×ATR, target: 4×ATR)
ml_threshold = 0.30            # ML probability threshold
```

## 🔍 Key Features

✅ **Automated Signal Generation**: ML-driven entry/exit signals  
✅ **Multi-Stock Portfolio**: Diversified across 15 NSE stocks  
✅ **Regime-Aware Trading**: HMM-based market state detection  
✅ **Risk Management**: ATR-based stops, position limits, portfolio risk caps  
✅ **Backtesting Engine**: Historical performance validation  
✅ **Performance Tracking**: Detailed metrics and per-symbol breakdown  
✅ **Professional-Grade Returns**: 46.8% CAGR over 5 years  

## 📊 Performance Metrics Explained

- **Total Return**: 234.39% (capital grew 3.34x)
- **CAGR**: 46.8% (compound annual growth rate)
- **Monthly Return**: 3.85% average
- **Win Rate**: 52.16% (133 wins, 122 losses)
- **Sharpe Ratio**: 0.49 (risk-adjusted returns)
- **Max Drawdown**: Portfolio-level risk control
- **Profit Factor**: Gross profits / Gross losses

## 🎯 Future Enhancements

### Short-term (Ready to Implement)
- [ ] Increase max positions from 5 to 7-10
- [ ] Add more NSE stocks (50+ liquid stocks available)
- [ ] Implement trailing stops for winning trades
- [ ] Add portfolio-level monthly stop loss

### Medium-term
- [ ] Sector-based capital allocation
- [ ] Multi-timeframe analysis (daily + weekly signals)
- [ ] Paper trading integration (live market testing)
- [ ] Real-time signal monitoring dashboard

### Long-term
- [ ] Intraday trading strategies (if minute data available)
- [ ] Options strategies integration
- [ ] Sentiment analysis (news, social media)
- [ ] Live broker integration (Zerodha, Angel One)

## ⚠️ Risk Disclaimer

**This system is for educational and research purposes.**

- Past performance does not guarantee future results
- Trading involves substantial risk of loss
- Backtest results may not reflect live trading conditions (slippage, liquidity, costs)
- Always paper trade before live deployment
- Never risk capital you cannot afford to lose
- Consider consulting a financial advisor

## 🤝 Contributing

This is a personal research project. If you'd like to:
- Report bugs or issues
- Suggest improvements
- Share backtesting results
- Collaborate on enhancements

Feel free to create issues or submit pull requests.

## 📝 License

This project is for personal use and educational purposes. All rights reserved.

## 📧 Contact

For questions or discussions about the system, please create an issue in the repository.

---

## 🏆 Summary

**What started as a quest for 15-25% annual returns evolved into a sophisticated ML-enhanced portfolio system achieving 46.8% CAGR.**

The key breakthrough came from recognizing that **trade frequency matters as much as trade quality**. By scaling from single-stock to multi-stock portfolio:
- Single stock: 0.38 trades/month → 6.59% return
- Portfolio: 4.19 trades/month → 234.39% return

**The system is production-ready** and demonstrates that systematic, algorithmic trading can outperform traditional buy-and-hold strategies when combining:
1. Machine learning for signal quality
2. Regime detection for context awareness  
3. Portfolio diversification for opportunity multiplication
4. Rigorous risk management for capital preservation

---

*Last Updated: February 2026*  
*Backtest Period: 2020-2024 (5 years)*  
*Market: National Stock Exchange of India (NSE)*
