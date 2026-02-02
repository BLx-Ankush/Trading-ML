"""Debug trending signal formula."""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import pandas as pd
from src.data.data_loader import DataLoader
from src.data.data_processor import DataProcessor
from src.features.indicators import TechnicalIndicators
from src.models.hmm_regime import RegimeDetector

# Load data
loader = DataLoader()
data = loader.fetch_yahoo_data("RELIANCE.NS", "2020-01-01", "2024-12-31")
data = DataProcessor.clean_data(data)
data = TechnicalIndicators.calculate_all_indicators(data)

# Load regimes
regime_detector = RegimeDetector(n_states=3)
regime_detector.load('data/models/hmm_regime_model.pkl')
_, regimes = regime_detector.predict(data)

print(f"\n{'='*80}")
print(f"TRENDING SIGNAL FORMULA DEBUG")
print(f"{'='*80}")

# Check first 20 trending days
trending_samples = []
for i in range(30, len(data)):
    if regimes[i] == 'trending':
        bar = data.iloc[i]
        
        price = bar['close']
        ema20 = bar['ema_20']
        rsi = bar['rsi']
        adx = bar['adx']
        atr = bar['atr']
        
        if all(x is not None for x in [price, ema20, rsi, adx, atr]):
            # Calculate fuzzy scores
            rsi_weight = max(0.0, min(1.0, (rsi - 20) / 60))
            trend_weight = max(0.0, min(1.0, abs(price - ema20) / (atr * 0.5)))
            adx_weight = max(0.0, min(1.0, (adx - 5) / 25))
            total_score = rsi_weight + trend_weight + adx_weight
            
            trending_samples.append({
                'date': bar.name,
                'price': price,
                'ema20': ema20,
                'rsi': rsi,
                'adx': adx,
                'atr': atr,
                'rsi_weight': rsi_weight,
                'trend_weight': trend_weight,
                'adx_weight': adx_weight,
                'total_score': total_score,
                'signal': 'YES' if total_score > 0.4 else 'NO'
            })
        
        if len(trending_samples) >= 20:
            break

print(f"\nFirst 20 TRENDING days:")
print(f"{'Date':<12} {'RSI':>6} {'ADX':>6} {'P/EMA':>7} {'R_wt':>6} {'T_wt':>6} {'A_wt':>6} {'Total':>6} Signal")
print("-"*80)

for s in trending_samples:
    p_ema_ratio = s['price'] / s['ema20'] - 1
    print(f"{str(s['date'].date()):<12} {s['rsi']:>6.1f} {s['adx']:>6.1f} {p_ema_ratio:>6.1%} {s['rsi_weight']:>6.3f} {s['trend_weight']:>6.3f} {s['adx_weight']:>6.3f} {s['total_score']:>6.3f} {s['signal']}")

print(f"\n{'='*80}")
print(f"STATISTICS:")
print(f"{'='*80}")
df = pd.DataFrame(trending_samples)
print(f"Signals generated: {(df['signal'] == 'YES').sum()} / {len(df)}")
print(f"Average total score: {df['total_score'].mean():.3f}")
print(f"Max total score: {df['total_score'].max():.3f}")
print(f"Min total score: {df['total_score'].min():.3f}")
print(f"\nScore breakdown:")
print(f"  RSI weight avg: {df['rsi_weight'].mean():.3f}")
print(f"  Trend weight avg: {df['trend_weight'].mean():.3f}")
print(f"  ADX weight avg: {df['adx_weight'].mean():.3f}")
print(f"{'='*80}")
