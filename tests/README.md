# Trading System Tests - Phase 6A

This folder contains all test scripts for validating the Phase 6A production system.

## 🔥 Production Tests (Use These)

### **validate_production_system.py**
- **Purpose:** Complete production system validation on 2025 unseen data
- **What it tests:** Full system with ALL Phase 6A improvements
- **Expected result:** 18.41% net return, 5/5 criteria passed
- **Usage:**
```bash
python validate_production_system.py
```

### **test_phase6a_final.py**
- **Purpose:** Comprehensive comparison across all Phase 6A weeks
- **What it tests:** Evolution from baseline to final system
- **Expected result:** Performance evolution report, improvement breakdown
- **Usage:**
```bash
python test_phase6a_final.py
```

## 📊 Phase 6A Validation Tests

### **test_phase6a_week3.py**
- **Purpose:** Week 3 - Sector diversification validation
- **What it tests:** Sector limits (max 2 banking, max 2 IT)
- **Expected result:** 18.41% net return with sector analysis
- **Status:** ✅ Passing

### **test_phase6a_week2.py**
- **Purpose:** Week 2 - Problem stock filter validation
- **What it tests:** ICICIBANK exclusion, KOTAKBANK/ITC threshold increases
- **Expected result:** 18.24% net return, improved win rate
- **Status:** ✅ Passing

### **test_phase6a_costs.py**
- **Purpose:** Week 1 - Trading cost implementation validation
- **What it tests:** Slippage, brokerage, STT calculations
- **Expected result:** 15.65% net return with cost breakdown
- **Status:** ✅ Passing

## 🔬 Component Tests

### **test_2025_validation.py**
- **Purpose:** Basic 2025 out-of-sample validation
- **What it tests:** System on unseen 2025 data
- **Usage:** Quick validation check
- **Status:** ✅ Passing

### **test_ml_2025_validation.py**
- **Purpose:** ML system validation on 2025 data
- **What it tests:** Machine learning entry signals
- **Usage:** Verify ML model performance
- **Status:** ✅ Passing

### **test_costs_simple.py**
- **Purpose:** Unit test for cost calculation logic
- **What it tests:** Trading cost formulas (0.68% per round trip)
- **Usage:** Verify cost calculation accuracy
- **Status:** ✅ Passing

## 🏃 Quick Test Commands

### **Run Full Validation**
```bash
# Complete system validation
python validate_production_system.py

# Expected output:
# Net Return: 18.41%
# Win Rate: 61.76%
# Sharpe: 2.17
# All 5 criteria: PASSED
```

### **Run Phase 6A Comparison**
```bash
# Complete evolution report
python test_phase6a_final.py

# Expected output:
# Week 1: 15.65% (costs baseline)
# Week 2: 18.24% (+2.59% improvement)
# Week 3: 18.41% (+0.17% improvement)
# Final: 5/5 criteria PASSED
```

### **Test Individual Week**
```bash
# Week 3 validation
python test_phase6a_week3.py

# Week 2 validation
python test_phase6a_week2.py

# Week 1 validation
python test_phase6a_costs.py
```

## 📋 Test Status Summary

| Test Script | Purpose | Status | Last Run |
|------------|---------|--------|----------|
| validate_production_system.py | Production validation | ✅ Passing | Feb 2, 2026 |
| test_phase6a_final.py | Complete comparison | ✅ Passing | Feb 2, 2026 |
| test_phase6a_week3.py | Sector diversification | ✅ Passing | Feb 1, 2026 |
| test_phase6a_week2.py | Problem stock filters | ✅ Passing | Feb 1, 2026 |
| test_phase6a_costs.py | Trading costs | ✅ Passing | Jan 30, 2026 |
| test_2025_validation.py | Basic 2025 test | ✅ Passing | Jan 28, 2026 |
| test_ml_2025_validation.py | ML validation | ✅ Passing | Jan 28, 2026 |
| test_costs_simple.py | Cost unit tests | ✅ Passing | Jan 30, 2026 |

All tests: ✅ **PASSING**

## 🎯 Expected Performance (2025 Out-of-Sample)

```
Net Return:          18.41%
Annualized:          18.70%
Win Rate:            61.76%
Sharpe Ratio:        2.17
Profit Factor:       2.69
Max Drawdown:        2.71%
Total Trades:        34
Cost per Trade:      Rs. 314

Deployment Criteria: 5/5 PASSED ✅
```

## 🔍 Troubleshooting

### **Test Fails with Import Error**
```bash
# Activate virtual environment
D:\ProjectAlice\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### **Test Shows Different Results**
- Verify you're using correct config: `config/phase6a_production.yaml`
- Check date range: 2025-01-01 to 2025-12-31
- Ensure all Phase 6A improvements are enabled in config

### **Unicode Errors on Windows**
```bash
# Set UTF-8 encoding before running
$env:PYTHONIOENCODING='utf-8'
python validate_production_system.py
```

## 📝 Adding New Tests

When creating new test scripts:

1. **Name convention:** `test_<feature>_<purpose>.py`
2. **Import structure:**
```python
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
import run_portfolio
```

3. **Use production config:**
```python
config_path = 'config/phase6a_production.yaml'
```

4. **Document expected results:**
```python
"""
Expected Results:
- Net Return: 18.41%
- Win Rate: 61.76%
- Sharpe: 2.17
"""
```

5. **Add to this README** with status and expected output

---

**Last Updated:** February 2, 2026  
**System Status:** ✅ All tests passing, ready for paper trading
