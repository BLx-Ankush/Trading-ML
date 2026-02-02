"""
Test Phase 2: HMM Regime Detection + Strategy Selection

Tests the system with:
- HMM regime detection to identify market conditions
- Strategy selector to filter trades based on regime
- Same risk management and position sizing as Phase 1
- Compare results with Phase 1 random entries
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns

from src.data.data_loader import DataLoader
from src.data.data_processor import DataProcessor
from src.features.indicators import TechnicalIndicators
from src.models.garch import GARCHVolatility
from src.models.hmm_regime import RegimeDetector
from src.strategy.strategy_selector import StrategySelector
from src.risk.position_sizing import PositionSizer
from src.risk.risk_manager import RiskManager
from src.execution.executor import OrderExecutor
from src.backtesting.engine import Backtest
from src.backtesting.performance import PerformanceAnalyzer
from src.utils.config_loader import load_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


def test_phase2_regime_based():
    """Test Phase 2 with HMM regime detection."""
    
    logger.info("=" * 80)
    logger.info("PHASE 2: HMM REGIME DETECTION + STRATEGY SELECTION")
    logger.info("=" * 80)
    
    # Load configuration
    config = load_config()
    
    # Initialize components
    data_loader = DataLoader(config)
    data_processor = DataProcessor(config)
    indicators = TechnicalIndicators()
    
    # Stocks to test
    stocks = [
        "RELIANCE.NS",
        "TCS.NS",
        "INFY.NS",
        "HDFCBANK.NS",
        "ICICIBANK.NS"
    ]
    
    # Load and prepare data
    logger.info("\nLoading historical data...")
    start_date = "2020-01-01"
    end_date = "2024-12-31"
    
    all_data = {}
    for symbol in stocks:
        raw_data = data_loader.load_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )
        
        if raw_data.empty:
            logger.warning(f"No data for {symbol}, skipping...")
            continue
        
        # Process data
        clean_data = data_processor.process(raw_data)
        
        # Add technical indicators
        clean_data = indicators.add_all_indicators(clean_data)
        
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
    combined_data = pd.concat([df for df in all_data.values()])
    
    regime_detector = RegimeDetector(n_states=3, random_state=42)
    regime_detector.fit(combined_data)
    
    # Save model
    model_path = "data/models/hmm_regime_model.pkl"
    regime_detector.save(model_path)
    
    # Backtest with regime filtering
    logger.info("\n" + "=" * 80)
    logger.info("BACKTESTING WITH REGIME FILTERING")
    logger.info("=" * 80)
    
    # Initialize strategy selector
    strategy_selector = StrategySelector()
    
    # Run backtest for each stock
    all_results = []
    
    for symbol, data in all_data.items():
        logger.info(f"\nBacktesting {symbol}...")
        
        # Predict regimes for this stock
        _, regimes = regime_detector.predict(data)
        
        # Add regime column
        regime_series = pd.Series(regimes, index=data.index[-len(regimes):])
        data_with_regime = data.copy()
        data_with_regime['regime'] = regime_series
        
        # Forward fill regime for missing values
        data_with_regime['regime'] = data_with_regime['regime'].ffill()
        
        # Log regime distribution
        regime_counts = pd.Series(regimes).value_counts()
        logger.info(f"Regime distribution for {symbol}:")
        for regime, count in regime_counts.items():
            pct = count / len(regimes) * 100
            logger.info(f"  {regime}: {count} days ({pct:.1f}%)")
        
        # Initialize backtest components
        garch_model = GARCHVolatility()
        position_sizer = PositionSizer(config)
        risk_manager = RiskManager(config)
        executor = OrderExecutor(config)
        
        # Create custom signal generator with regime filtering
        def regime_signal_generator(row, position):
            """Generate signals based on regime and strategy selector."""
            
            # Get current regime
            regime = row.get('regime', 'ranging')
            
            # Skip if not a trading regime
            if not strategy_selector.should_trade(regime):
                return None
            
            # Get indicators for strategy selector
            indicators_dict = {
                'ema_20': row.get('ema_20'),
                'rsi': row.get('rsi'),
                'adx': row.get('adx'),
                'bb_lower': row.get('bb_lower'),
                'bb_upper': row.get('bb_upper')
            }
            
            # Get signal from strategy selector
            signal = strategy_selector.get_entry_signal(
                regime=regime,
                price=row['close'],
                indicators=indicators_dict
            )
            
            # For Phase 2 testing, we'll still use some randomness
            # but only in favorable regimes
            if signal == 'LONG':
                # 30% probability to actually take the trade
                if np.random.random() < 0.30:
                    return 'LONG'
            
            return None
        
        # Run backtest
        engine = BacktestEngine(
            data=data_with_regime,
            garch_model=garch_model,
            position_sizer=position_sizer,
            risk_manager=risk_manager,
            executor=executor,
            initial_capital=config['trading']['initial_capital']
        )
        
        results = engine.run(
            signal_generator=regime_signal_generator,
            name=f"{symbol} - Phase 2 (Regime-Based)"
        )
        
        all_results.append({
            'symbol': symbol,
            **results
        })
    
    # Aggregate results
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 2 AGGREGATE RESULTS")
    logger.info("=" * 80)
    
    total_return = np.mean([r['total_return'] for r in all_results])
    total_trades = np.sum([r['total_trades'] for r in all_results])
    avg_win_rate = np.mean([r['win_rate'] for r in all_results])
    avg_sharpe = np.mean([r['sharpe_ratio'] for r in all_results])
    max_dd = np.max([r['max_drawdown'] for r in all_results])
    
    logger.info(f"\nAverage Total Return: {total_return:.2%}")
    logger.info(f"Total Trades: {total_trades}")
    logger.info(f"Average Win Rate: {avg_win_rate:.2%}")
    logger.info(f"Average Sharpe Ratio: {avg_sharpe:.2f}")
    logger.info(f"Max Drawdown: {max_dd:.2%}")
    
    # Print individual results
    logger.info("\n" + "-" * 80)
    logger.info("INDIVIDUAL STOCK RESULTS")
    logger.info("-" * 80)
    
    for result in all_results:
        logger.info(f"\n{result['symbol']}:")
        logger.info(f"  Total Return: {result['total_return']:.2%}")
        logger.info(f"  Trades: {result['total_trades']}")
        logger.info(f"  Win Rate: {result['win_rate']:.2%}")
        logger.info(f"  Sharpe: {result['sharpe_ratio']:.2f}")
        logger.info(f"  Max DD: {result['max_drawdown']:.2%}")
    
    # Print strategy statistics
    strategy_selector.print_stats()
    
    # Save results
    results_df = pd.DataFrame(all_results)
    output_dir = Path("backtest_results/phase2")
    output_dir.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(output_dir / "phase2_results.csv", index=False)
    
    logger.info(f"\nResults saved to {output_dir}")
    
    # Comparison with Phase 1
    logger.info("\n" + "=" * 80)
    logger.info("COMPARISON: PHASE 1 vs PHASE 2")
    logger.info("=" * 80)
    
    logger.info("\nPhase 1 (Random Entries):")
    logger.info("  Total Return: 24.47% (5 years)")
    logger.info("  Win Rate: 61.25%")
    logger.info("  Sharpe: 1.37")
    logger.info("  Max DD: 3.05%")
    
    logger.info(f"\nPhase 2 (Regime-Based):")
    logger.info(f"  Total Return: {total_return:.2%} (5 years)")
    logger.info(f"  Win Rate: {avg_win_rate:.2%}")
    logger.info(f"  Sharpe: {avg_sharpe:.2f}")
    logger.info(f"  Max DD: {max_dd:.2%}")
    
    improvement = ((total_return - 0.2447) / 0.2447) * 100
    logger.info(f"\nImprovement: {improvement:+.1f}%")
    
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 2 TEST COMPLETE")
    logger.info("=" * 80)


if __name__ == "__main__":
    test_phase2_regime_based()
