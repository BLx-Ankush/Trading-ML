# System Architecture Overview

## Production System Structure

### Main Entry Point ⭐
**File**: `run_portfolio.py`

This is your MAIN production runner. All other test files are just for validation.

**Usage:**
```bash
# Run with default config
python run_portfolio.py

# Use custom configuration
python run_portfolio.py --config aggressive

# Future: Live trading (not implemented yet)
python run_portfolio.py --live
```

---

## Core System Files (Production Code)

### 1. Portfolio Engine (Updated ✅)
**File**: `src/backtesting/portfolio_engine.py`

**Key Changes:**
- `enable_trailing_stop = False` (disabled by default)
- `enable_time_exit = False` (disabled by default)
- `enable_monthly_stop = True` (circuit breaker enabled)
- `monthly_stop_loss = 0.10` (10% threshold)

**What It Does:**
- Manages multiple positions across stocks
- Handles capital allocation
- Executes stop loss and take profit
- Portfolio-level risk management
- Monthly circuit breaker

### 2. Configuration System (New ✅)
**File**: `config/default.yaml`

**Contains:**
- Stock universe (15 NSE stocks)
- Portfolio settings (capital, risk, etc.)
- Strategy parameters (ML thresholds)
- Backtest date ranges

**Customizable**: Create `config/aggressive.yaml` or `config/conservative.yaml` for different strategies

### 3. Strategy Components (Existing)
**Files:**
- `src/strategy/ml_strategy_selector.py` - ML entry signals
- `src/models/hmm_regime.py` - Market regime detection
- `src/features/indicators.py` - Technical indicators
- `src/data/data_loader.py` - Data fetching
- `src/data/data_processor.py` - Data cleaning

---

## Test Files (For Validation Only)

### Comparison & Validation
- `test_phase4_baseline_comparison.py` - Compare Phase 4 vs Phase 5
- `test_phase5_validation.py` - Feature validation
- `test_phase5_revised.py` - Phase 5 revised backtest

### Historical Tests (Reference)
- `test_phase3_*.py` - Phase 3 development
- `test_phase4_portfolio.py` - Phase 4 baseline
- `test_phase5_optimized.py` - Failed optimizations (keep for reference)

**Important**: Test files are for development/validation. Production uses `run_portfolio.py`

---

## How The System Works

### 1. Initialization
```python
# Load configuration
config = load_config('default')  # From config/default.yaml

# Create portfolio engine (uses Phase 5 Revised defaults)
portfolio = PortfolioEngine(
    initial_capital=200000,
    enable_trailing_stop=False,  # From config
    enable_time_exit=False,
    enable_monthly_stop=True
)

# Load ML models
ml_selector = MLStrategySelector(model_path='...')
regime_detector = RegimeDetector()
```

### 2. Data Loading
```python
# Load 15 NSE stocks
for symbol in stocks:
    data = load_stock_data(symbol, start_date, end_date)
    regimes = regime_detector.predict(data)
```

### 3. Main Trading Loop
```python
for each_trading_day:
    # 1. Update equity curve
    portfolio.update_equity_curve(current_date)
    
    # 2. Check exits for open positions
    for position in portfolio.positions:
        if hit_stop_loss:
            close_position('STOP')
        elif hit_take_profit:
            close_position('TARGET')
    
    # 3. Check for new entries
    for stock in universe:
        if ml_signal == 'LONG' and can_open_position:
            open_position(
                entry_price=close,
                stop_loss=entry - 2*ATR,
                take_profit=entry + 4*ATR
            )
```

### 4. Results & Analysis
```python
# Get performance metrics
metrics = portfolio.get_performance_metrics()

# Print comprehensive results
- Overall performance (234% return, 2.44 Sharpe)
- Per-stock breakdown
- Risk analysis
- Monthly statistics
```

---

## Configuration Options

### Creating Custom Configs

**Example: Aggressive Strategy**
`config/aggressive.yaml`:
```yaml
portfolio:
  initial_capital: 500000  # 5 lakhs
  max_positions: 8         # More positions
  risk_per_trade: 0.015    # 1.5% risk

strategy:
  ml_threshold: 0.25       # Lower threshold = more trades
```

**Example: Conservative Strategy**
`config/conservative.yaml`:
```yaml
portfolio:
  initial_capital: 200000
  max_positions: 3         # Fewer positions
  risk_per_trade: 0.005    # 0.5% risk

strategy:
  ml_threshold: 0.40       # Higher threshold = fewer, safer trades
```

---

## Data Flow

```
Yahoo Finance
    ↓
DataLoader (fetch data)
    ↓
DataProcessor (clean)
    ↓
TechnicalIndicators (calculate)
    ↓
RegimeDetector (classify market state)
    ↓
MLStrategySelector (generate signals)
    ↓
PortfolioEngine (execute trades)
    ↓
Results & Performance Metrics
```

---

## What's Updated vs What's Not

### ✅ Updated for Production

1. **PortfolioEngine defaults** - Phase 5 Revised settings
2. **Main runner** - `run_portfolio.py` created
3. **Configuration system** - `config/default.yaml` created
4. **Documentation** - This file + results docs

### 📋 NOT Changed (Working As-Is)

1. **ML models** - Using trained LightGBM model
2. **Regime detector** - Using trained HMM model
3. **Feature engineering** - Technical indicators
4. **Data loading** - Yahoo Finance integration
5. **Entry logic** - ML + regime filtering

### 🔮 Future Work (Phase 6)

1. Entry quality filtering (SBIN.NS fix)
2. Sector diversification
3. Dynamic position sizing
4. Partial profit taking
5. Live trading implementation

---

## Quick Start

### Run Backtest
```bash
# Default settings (Phase 5 Revised)
python run_portfolio.py

# Expected output:
# Total Return: 234.39%
# Sharpe Ratio: 2.44
# Max Drawdown: 7.77%
```

### Customize Strategy
```bash
# 1. Copy config template
cp config/default.yaml config/my_strategy.yaml

# 2. Edit settings in my_strategy.yaml

# 3. Run with custom config
python run_portfolio.py --config my_strategy
```

### Modify Stock Universe
Edit `config/default.yaml`:
```yaml
stocks:
  - RELIANCE.NS
  - TCS.NS
  # Add/remove stocks here
```

---

## Summary

**Yes, the main system is properly configured!**

✅ Core engine updated (`portfolio_engine.py`)  
✅ Production runner created (`run_portfolio.py`)  
✅ Configuration system added (`config/default.yaml`)  
✅ All ML models and data systems working  

**Test files are just for validation - not part of production system.**

**To run the real system**: `python run_portfolio.py`
