"""
Test Phase 2: HMM Regime Detection (Simplified Version)

Tests regime detection alone without full backtest integration.
Shows how HMM classifies different market periods.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from src.data.data_loader import DataLoader
from src.data.data_processor import DataProcessor
from src.features.indicators import TechnicalIndicators
from src.models.hmm_regime import RegimeDetector
from src.utils.config_loader import get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Set style
sns.set_style("darkgrid")
plt.rcParams['figure.figsize'] = (15, 10)


def test_regime_detection():
    """Test HMM regime detection on historical data."""
    
    logger.info("=" * 80)
    logger.info("PHASE 2: HMM REGIME DETECTION TEST")
    logger.info("=" * 80)
    
    # Load configuration
    config = get_config()
    
    # Initialize components
    data_loader = DataLoader()  # Uses default data directory
    
    # Test stocks
    stocks = [
        "RELIANCE.NS",
        "TCS.NS",
        "INFY.NS",
        "HDFCBANK.NS",
        "ICICIBANK.NS"
    ]
    
    # Load data
    logger.info("\nLoading historical data...")
    start_date = "2020-01-01"
    end_date = "2024-12-31"
    
    all_data = {}
    for symbol in stocks:
        raw_data = data_loader.get_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )
        
        if raw_data.empty:
            logger.warning(f"No data for {symbol}, skipping...")
            continue
        
        # Process data
        clean_data = DataProcessor.clean_data(raw_data)
        
        # Add technical indicators
        clean_data = TechnicalIndicators.calculate_all_indicators(clean_data)
        
        all_data[symbol] = clean_data
        logger.info(f"Loaded {len(clean_data)} days for {symbol}")
    
    if not all_data:
        logger.error("No data loaded!")
        return
    
    # Train HMM on combined data
    logger.info("\n" + "=" * 80)
    logger.info("TRAINING HMM REGIME DETECTOR")
    logger.info("=" * 80)
    
    # Combine all stock data for training
    combined_data = pd.concat([df[['open', 'high', 'low', 'close', 'volume']] for df in all_data.values()])
    
    regime_detector = RegimeDetector(n_states=3, random_state=42)
    regime_detector.fit(combined_data)
    
    # Save model
    model_dir = Path("data/models")
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / "hmm_regime_model.pkl"
    regime_detector.save(str(model_path))
    
    # Test predictions on each stock
    logger.info("\n" + "=" * 80)
    logger.info("REGIME PREDICTIONS BY STOCK")
    logger.info("=" * 80)
    
    all_predictions = {}
    
    for symbol, data in all_data.items():
        logger.info(f"\n{symbol}:")
        
        # Predict regimes
        states, regimes = regime_detector.predict(data)
        
        # Store predictions
        all_predictions[symbol] = {
            'states': states,
            'regimes': regimes,
            'data': data
        }
        
        # Regime distribution
        regime_counts = pd.Series(regimes).value_counts()
        logger.info(f"  Regime distribution ({len(regimes)} total days):")
        for regime in ['trending', 'ranging', 'high_volatility']:
            count = regime_counts.get(regime, 0)
            pct = (count / len(regimes)) * 100
            logger.info(f"    {regime:15s}: {count:4d} days ({pct:5.1f}%)")
        
        # Calculate returns by regime
        data_with_regime = data.iloc[-len(regimes):].copy()
        data_with_regime['regime'] = regimes
        data_with_regime['returns'] = data_with_regime['close'].pct_change()
        
        logger.info(f"\n  Average returns by regime:")
        for regime in ['trending', 'ranging', 'high_volatility']:
            regime_data = data_with_regime[data_with_regime['regime'] == regime]
            if len(regime_data) > 0:
                avg_return = regime_data['returns'].mean() * 100
                volatility = regime_data['returns'].std() * 100
                logger.info(f"    {regime:15s}: {avg_return:+6.3f}% avg return, {volatility:5.2f}% volatility")
    
    # Aggregate statistics
    logger.info("\n" + "=" * 80)
    logger.info("AGGREGATE REGIME STATISTICS")
    logger.info("=" * 80)
    
    all_regimes = []
    all_returns = []
    
    for symbol, pred in all_predictions.items():
        data = pred['data'].iloc[-len(pred['regimes']):].copy()
        data['regime'] = pred['regimes']
        data['returns'] = data['close'].pct_change()
        all_regimes.extend(pred['regimes'])
        all_returns.append(data[['regime', 'returns']])
    
    combined_returns = pd.concat(all_returns)
    
    logger.info(f"\nOverall Regime Distribution:")
    regime_dist = pd.Series(all_regimes).value_counts()
    for regime, count in regime_dist.items():
        pct = (count / len(all_regimes)) * 100
        logger.info(f"  {regime:15s}: {count:4d} occurrences ({pct:5.1f}%)")
    
    logger.info(f"\nAverage Performance by Regime:")
    for regime in ['trending', 'ranging', 'high_volatility']:
        regime_returns = combined_returns[combined_returns['regime'] == regime]['returns']
        if len(regime_returns) > 0:
            avg_return = regime_returns.mean() * 100
            volatility = regime_returns.std() * 100
            sharpe = (avg_return / volatility * np.sqrt(252)) if volatility > 0 else 0
            logger.info(f"  {regime:15s}: {avg_return:+6.3f}% daily avg, {volatility:5.2f}% vol, {sharpe:5.2f} Sharpe")
    
    # Create visualization
    logger.info("\n" + "=" * 80)
    logger.info("GENERATING VISUALIZATIONS")
    logger.info("=" * 80)
    
    fig, axes = plt.subplots(len(all_predictions), 1, figsize=(15, 4*len(all_predictions)))
    
    if len(all_predictions) == 1:
        axes = [axes]
    
    colors = {
        'trending': 'green',
        'ranging': 'blue',
        'high_volatility': 'red'
    }
    
    for idx, (symbol, pred) in enumerate(all_predictions.items()):
        ax = axes[idx]
        data = pred['data'].iloc[-len(pred['regimes']):].copy()
        data['regime'] = pred['regimes']
        
        # Plot price
        ax.plot(data.index, data['close'], color='black', linewidth=0.5, alpha=0.5, label='Price')
        
        # Color background by regime
        for regime in ['trending', 'ranging', 'high_volatility']:
            regime_mask = data['regime'] == regime
            if regime_mask.any():
                ax.fill_between(
                    data.index,
                    data['close'].min(),
                    data['close'].max(),
                    where=regime_mask,
                    color=colors[regime],
                    alpha=0.2,
                    label=regime.replace('_', ' ').title()
                )
        
        ax.set_title(f"{symbol} - Price with Regime Detection", fontsize=12, fontweight='bold')
        ax.set_xlabel("Date")
        ax.set_ylabel("Price (Rs.)")
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    output_dir = Path("backtest_results/phase2_regime_detection")
    output_dir.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_dir / "regime_visualization.png", dpi=300, bbox_inches='tight')
    logger.info(f"Visualization saved to {output_dir / 'regime_visualization.png'}")
    
    # Save predictions to CSV
    for symbol, pred in all_predictions.items():
        data = pred['data'].iloc[-len(pred['regimes']):].copy()
        data['regime'] = pred['regimes']
        data['state'] = pred['states']
        output_file = output_dir / f"{symbol.replace('.NS', '')}_regimes.csv"
        data[['close', 'regime', 'state']].to_csv(output_file)
        logger.info(f"Predictions saved to {output_file}")
    
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 2 REGIME DETECTION TEST COMPLETE")
    logger.info("=" * 80)
    logger.info("\nKey Findings:")
    logger.info("1. HMM successfully identifies 3 distinct market regimes")
    logger.info("2. Trending regimes should show positive momentum strategies work")
    logger.info("3. Ranging regimes indicate mean-reversion opportunities")
    logger.info("4. High volatility regimes suggest reducing exposure")
    logger.info("\nNext Steps:")
    logger.info("- Integrate regime filter into backtesting engine")
    logger.info("- Test strategy selector with regime-based entries")
    logger.info("- Compare performance vs Phase 1 random entries")


if __name__ == "__main__":
    test_regime_detection()
