"""
Monte Carlo Simulation: DIFFERENT STOCKS VALIDATION
Testing on completely different set of Indian stocks to prove no overfitting.
Same time period: 2020-2024
"""
import random
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict, List
from tqdm import tqdm

from src.backtesting import Backtest, PerformanceAnalyzer
from src.utils.logger import get_logger

logger = get_logger()


def random_signal_generator(df: pd.DataFrame, current_index: int) -> Dict:
    """Generate random trading signals."""
    if current_index < 50:
        return None
    
    if pd.isna(df.iloc[current_index]['atr']):
        return None
    
    if random.random() < 0.10:  # 10% chance
        return {
            'action': 'buy',
            'confidence': random.uniform(0.5, 1.0),
            'strategy': 'random_entry'
        }
    
    return None


def run_single_backtest(risk_reward_ratio: float, seed: int, config: Dict) -> Dict:
    """Run a single backtest with specified R:R ratio and random seed."""
    random.seed(seed)
    np.random.seed(seed)
    
    backtest = Backtest(
        initial_capital=config['initial_capital'],
        start_date=config['start_date'],
        end_date=config['end_date'],
        symbols=config['symbols'],
        slippage=config['slippage'],
        commission=config['commission']
    )
    
    backtest.load_data()
    
    try:
        results = backtest.run(
            signal_generator=random_signal_generator,
            strategy_name=f"Validation Test (R:R={risk_reward_ratio})"
        )
        
        return {
            'seed': seed,
            'rr_ratio': risk_reward_ratio,
            'total_return': results['total_return'],
            'final_capital': results['final_capital'],
            'win_rate': results['win_rate'],
            'total_trades': results['total_trades'],
            'max_drawdown': results['max_drawdown'],
            'sharpe_ratio': results['sharpe_ratio'],
            'win_loss_ratio': results['win_loss_ratio'],
            'avg_win': results['avg_win'],
            'avg_loss': results['avg_loss']
        }
    except Exception as e:
        logger.error(f"Backtest failed for seed {seed}: {e}")
        return None


def run_monte_carlo_simulation(num_simulations: int = 1000) -> pd.DataFrame:
    """Run Monte Carlo simulation comparing different stocks."""
    
    print("\n" + "="*80)
    print("VALIDATION TEST: DIFFERENT STOCKS (2020-2024)")
    print("="*80)
    print(f"\nRunning {num_simulations} simulations on DIFFERENT stocks...")
    print("\nOriginal Stocks: RELIANCE, TCS, INFY, HDFCBANK, ICICIBANK")
    print("New Stocks: WIPRO, BHARTIARTL, MARUTI, SBIN, LT")
    print("\nTesting to prove NO OVERFITTING...\n")
    
    # Configuration with DIFFERENT stocks
    config = {
        'initial_capital': 200000,
        'start_date': "2020-01-01",
        'end_date': "2024-12-31",
        'symbols': [
            'WIPRO.NS',       # IT Services (instead of TCS)
            'BHARTIARTL.NS',  # Telecom (new sector)
            'MARUTI.NS',      # Automobile (new sector)
            'SBIN.NS',        # Public Bank (instead of HDFC/ICICI)
            'LT.NS'           # Engineering (new sector)
        ],
        'slippage': 0.001,
        'commission': 0.0003
    }
    
    print("Stock Details:")
    print("  • WIPRO.NS: Wipro Ltd (IT Services)")
    print("  • BHARTIARTL.NS: Bharti Airtel (Telecom)")
    print("  • MARUTI.NS: Maruti Suzuki (Automobiles)")
    print("  • SBIN.NS: State Bank of India (Banking)")
    print("  • LT.NS: Larsen & Toubro (Engineering/Construction)")
    print("\nThis will take 30-60 minutes. Please be patient...\n")
    
    all_results = []
    
    # Run simulations
    for i in tqdm(range(num_simulations), desc="Running simulations"):
        seed = 42 + i
        
        result = run_single_backtest(
            risk_reward_ratio=2.0,
            seed=seed,
            config=config
        )
        
        if result:
            all_results.append(result)
    
    results_df = pd.DataFrame(all_results)
    
    return results_df


def analyze_results(results_df: pd.DataFrame, output_dir: str = "backtest_results/validation_different_stocks"):
    """Analyze and visualize validation results."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "="*80)
    print("VALIDATION RESULTS - DIFFERENT STOCKS")
    print("="*80 + "\n")
    
    # Summary statistics
    print("SUMMARY STATISTICS")
    print("-"*80)
    
    metrics = ['total_return', 'win_rate', 'sharpe_ratio', 'max_drawdown', 'total_trades']
    
    for metric in metrics:
        mean_val = results_df[metric].mean()
        median_val = results_df[metric].median()
        std_val = results_df[metric].std()
        min_val = results_df[metric].min()
        max_val = results_df[metric].max()
        ci_lower = np.percentile(results_df[metric], 2.5)
        ci_upper = np.percentile(results_df[metric], 97.5)
        
        print(f"\n{metric.upper().replace('_', ' ')}:")
        print(f"  Mean:        {mean_val:>10.4f}")
        print(f"  Median:      {median_val:>10.4f}")
        print(f"  Std Dev:     {std_val:>10.4f}")
        print(f"  Min:         {min_val:>10.4f}")
        print(f"  Max:         {max_val:>10.4f}")
        print(f"  95% CI:      [{ci_lower:.4f}, {ci_upper:.4f}]")
    
    # Profitability analysis
    profitable = (results_df['total_return'] > 0).sum()
    total = len(results_df)
    prob_profit = (profitable / total) * 100
    
    print("\n" + "-"*80)
    print(f"PROFITABILITY: {profitable}/{total} simulations ({prob_profit:.1f}%)")
    print("-"*80)
    
    # Save detailed results
    results_file = output_path / "validation_results.csv"
    results_df.to_csv(results_file, index=False)
    print(f"\n✓ Detailed results saved to: {results_file}")
    
    # Create visualizations
    print("\nGenerating visualizations...")
    
    sns.set_style("whitegrid")
    
    # 1. Distribution plots
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    
    # Return histogram
    axes[0, 0].hist(results_df['total_return'] * 100, bins=50, edgecolor='black', alpha=0.7, color='green')
    axes[0, 0].axvline(results_df['total_return'].mean() * 100, color='red', 
                       linestyle='--', linewidth=2, label='Mean')
    axes[0, 0].axvline(0, color='gray', linestyle='-', linewidth=1)
    axes[0, 0].set_xlabel('Total Return (%)')
    axes[0, 0].set_ylabel('Frequency')
    axes[0, 0].set_title('Distribution of Returns - Different Stocks')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)
    
    # Win Rate histogram
    axes[0, 1].hist(results_df['win_rate'] * 100, bins=50, edgecolor='black', alpha=0.7, color='blue')
    axes[0, 1].axvline(results_df['win_rate'].mean() * 100, color='red', 
                       linestyle='--', linewidth=2, label='Mean')
    axes[0, 1].axvline(40, color='orange', linestyle='--', linewidth=2, label='Break-even (40%)')
    axes[0, 1].set_xlabel('Win Rate (%)')
    axes[0, 1].set_ylabel('Frequency')
    axes[0, 1].set_title('Distribution of Win Rates')
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)
    
    # Sharpe Ratio histogram
    axes[1, 0].hist(results_df['sharpe_ratio'], bins=50, edgecolor='black', alpha=0.7, color='purple')
    axes[1, 0].axvline(results_df['sharpe_ratio'].mean(), color='red', 
                       linestyle='--', linewidth=2, label='Mean')
    axes[1, 0].axvline(0, color='gray', linestyle='-', linewidth=1)
    axes[1, 0].set_xlabel('Sharpe Ratio')
    axes[1, 0].set_ylabel('Frequency')
    axes[1, 0].set_title('Distribution of Sharpe Ratios')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    # Max Drawdown histogram
    axes[1, 1].hist(results_df['max_drawdown'] * 100, bins=50, edgecolor='black', alpha=0.7, color='red')
    axes[1, 1].axvline(results_df['max_drawdown'].mean() * 100, color='darkred', 
                       linestyle='--', linewidth=2, label='Mean')
    axes[1, 1].set_xlabel('Max Drawdown (%)')
    axes[1, 1].set_ylabel('Frequency')
    axes[1, 1].set_title('Distribution of Max Drawdown')
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    dist_file = output_path / "distributions.png"
    plt.savefig(dist_file, dpi=150, bbox_inches='tight')
    print(f"✓ Distribution charts saved to: {dist_file}")
    plt.close()
    
    # 2. Comparison summary
    print("\n" + "="*80)
    print("VALIDATION TEST COMPLETE")
    print("="*80)
    print(f"\nKey Finding: With R:R = 2.0 and random entries on DIFFERENT stocks:")
    print(f"  • Expected Return: {results_df['total_return'].mean():.2%} ± {results_df['total_return'].std():.2%}")
    print(f"  • Expected Win Rate: {results_df['win_rate'].mean():.2%}")
    print(f"  • Probability of Profit: {prob_profit:.1f}%")
    print(f"  • Expected Sharpe: {results_df['sharpe_ratio'].mean():.2f}")
    print("\n" + "="*80 + "\n")


def main():
    """Run validation Monte Carlo simulation on different stocks."""
    
    # Run 1,000 simulations
    results_df = run_monte_carlo_simulation(num_simulations=1000)
    
    # Analyze results
    analyze_results(results_df)
    
    # Load original results for comparison
    print("\n" + "="*80)
    print("COMPARISON: ORIGINAL vs DIFFERENT STOCKS")
    print("="*80)
    
    try:
        original_df = pd.read_csv("backtest_results/monte_carlo/monte_carlo_results.csv")
        
        print("\n┌─────────────────────┬──────────────────┬──────────────────┬────────────┐")
        print("│ Metric              │ Original Stocks  │ Different Stocks │ Difference │")
        print("├─────────────────────┼──────────────────┼──────────────────┼────────────┤")
        
        metrics_compare = [
            ('Total Return', 'total_return', '%'),
            ('Win Rate', 'win_rate', '%'),
            ('Sharpe Ratio', 'sharpe_ratio', ''),
            ('Max Drawdown', 'max_drawdown', '%'),
            ('Profitability', None, '%')
        ]
        
        for label, metric, unit in metrics_compare:
            if metric:
                orig = original_df[metric].mean()
                new = results_df[metric].mean()
                diff = new - orig
                
                if unit == '%':
                    print(f"│ {label:<19} │ {orig*100:>14.2f}% │ {new*100:>14.2f}% │ {diff*100:>+9.2f}% │")
                else:
                    print(f"│ {label:<19} │ {orig:>16.2f} │ {new:>16.2f} │ {diff:>+10.2f} │")
            else:
                orig_prof = (original_df['total_return'] > 0).sum() / len(original_df) * 100
                new_prof = (results_df['total_return'] > 0).sum() / len(results_df) * 100
                diff_prof = new_prof - orig_prof
                print(f"│ {label:<19} │ {orig_prof:>14.2f}% │ {new_prof:>14.2f}% │ {diff_prof:>+9.2f}% │")
        
        print("└─────────────────────┴──────────────────┴──────────────────┴────────────┘")
        
        print("\n📊 CONCLUSION:")
        print("   If results are similar, the system is NOT overfitted!")
        print("   If results differ drastically, there may be stock-specific bias.")
        
    except FileNotFoundError:
        print("\n⚠️  Original results file not found. Run test_monte_carlo.py first.")


if __name__ == "__main__":
    main()
