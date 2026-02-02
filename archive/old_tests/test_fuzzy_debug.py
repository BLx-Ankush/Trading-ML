"""Debug: Check fuzzy signal generation rates."""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import pandas as pd
from src.data.data_loader import DataLoader
from src.data.data_processor import DataProcessor
from src.features.indicators import TechnicalIndicators
from src.models.hmm_regime import RegimeDetector
from src.strategy.strategy_selector import StrategySelector

# Load data
loader = DataLoader()
data = loader.fetch_yahoo_data("RELIANCE.NS", "2020-01-01", "2024-12-31")
data = DataProcessor.clean_data(data)
data = TechnicalIndicators.calculate_all_indicators(data)

# Load regimes
regime_detector = RegimeDetector(n_states=3)
regime_detector.load('data/models/hmm_regime_model.pkl')
_, regimes = regime_detector.predict(data)

# Test fuzzy selector
selector = StrategySelector()
signals = []

for i in range(30, len(data)):
    bar = data.iloc[i]
    regime = regimes[i]
    
    indicators = {
        'ema_20': bar.get('ema_20'),
        'rsi': bar.get('rsi'),
        'adx': bar.get('adx'),
        'atr': bar.get('atr'),
        'macd': bar.get('macd'),
        'macd_signal': bar.get('macd_signal'),
        'bb_upper': bar.get('bb_upper'),
        'bb_lower': bar.get('bb_lower'),
        'volume': bar.get('volume')
    }
    
    signal = selector.get_entry_signal(
        regime=regime,
        price=bar['close'],
        indicators=indicators,
        track_near_miss=False
    )
    
    if signal:
        signals.append({
            'date': bar.name,
            'regime': regime,
            'price': bar['close'],
            'rsi': bar.get('rsi'),
            'adx': bar.get('adx'),
            'signal': signal
        })

print(f"\n{'='*80}")
print(f"FUZZY SIGNAL GENERATION ANALYSIS")
print(f"{'='*80}")
print(f"Total days: {len(data) - 30}")
print(f"Fuzzy signals generated: {len(signals)}")
print(f"Generation rate: {len(signals)/(len(data)-30)*100:.1f}%")
print(f"\nTarget: 300-500 signals (25-40%)")
print(f"Current: {len(signals)} signals ({len(signals)/(len(data)-30)*100:.1f}%)")

print(f"\n{'='*80}")
print(f"REGIME BREAKDOWN")
print(f"{'='*80}")
regime_counts = pd.Series(regimes[30:]).value_counts()
for regime, count in regime_counts.items():
    regime_signals = [s for s in signals if s['regime'] == regime]
    print(f"{regime:18s}: {count:4d} days ({count/(len(data)-30)*100:5.1f}%) → {len(regime_signals):3d} signals ({len(regime_signals)/count*100 if count>0 else 0:5.1f}%)")

print(f"\n{'='*80}")
print(f"SAMPLE SIGNALS (First 10)")
print(f"{'='*80}")
for i, sig in enumerate(signals[:10]):
    print(f"{sig['date'].date()} | {sig['regime']:18s} | Price: {sig['price']:7.2f} | RSI: {sig['rsi']:5.1f} | ADX: {sig['adx']:5.1f}")

print(f"{'='*80}")
