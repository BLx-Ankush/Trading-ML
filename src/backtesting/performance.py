"""
Performance metrics and reporting.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict

from ..utils.logger import get_logger

logger = get_logger()


class PerformanceAnalyzer:
    """Analyze and visualize backtest performance."""
    
    @staticmethod
    def generate_report(results: Dict, output_dir: str = None) -> str:
        """
        Generate detailed performance report.
        
        Args:
            results: Results dictionary from backtest
            output_dir: Directory to save report
            
        Returns:
            Report text
        """
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
        
        report = []
        report.append("=" * 80)
        report.append("TRADING SYSTEM PERFORMANCE REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Overall Performance
        report.append("OVERALL PERFORMANCE")
        report.append("-" * 80)
        report.append(f"Initial Capital:        Rs.{results.get('initial_capital', 0):>15,.2f}")
        report.append(f"Final Capital:          Rs.{results['final_capital']:>15,.2f}")
        report.append(f"Total Return:            {results['total_return']:>15.2%}")
        report.append(f"Max Drawdown:            {results['max_drawdown']:>15.2%}")
        report.append(f"Sharpe Ratio:            {results['sharpe_ratio']:>15.2f}")
        report.append("")
        
        # Trade Statistics
        report.append("TRADE STATISTICS")
        report.append("-" * 80)
        report.append(f"Total Trades:            {results['total_trades']:>15,}")
        report.append(f"Winning Trades:          {results['winning_trades']:>15,}")
        report.append(f"Losing Trades:           {results['losing_trades']:>15,}")
        report.append(f"Win Rate:                {results['win_rate']:>15.2%}")
        report.append(f"Average Win:            Rs.{results['avg_win']:>15,.2f}")
        report.append(f"Average Loss:           Rs.{results['avg_loss']:>15,.2f}")
        report.append(f"Win/Loss Ratio:          {results['win_loss_ratio']:>15.2f}")
        report.append("")
        
        # Risk Metrics
        if 'trades' in results and not results['trades'].empty:
            trades_df = results['trades']
            
            report.append("RISK METRICS")
            report.append("-" * 80)
            report.append(f"Largest Win:            Rs.{trades_df['pnl'].max():>15,.2f}")
            report.append(f"Largest Loss:           Rs.{trades_df['pnl'].min():>15,.2f}")
            report.append(f"Average Hold Days:       {trades_df['hold_days'].mean():>15.1f}")
            report.append("")
        
        report_text = "\n".join(report)
        
        # Save to file if output_dir provided
        if output_dir:
            report_file = output_path / "performance_report.txt"
            with open(report_file, 'w') as f:
                f.write(report_text)
            logger.info(f"Report saved to {report_file}")
        
        return report_text
    
    @staticmethod
    def plot_equity_curve(equity_df: pd.DataFrame, output_dir: str = None):
        """Plot equity curve."""
        plt.figure(figsize=(12, 6))
        plt.plot(equity_df['date'], equity_df['total_equity'], label='Total Equity', linewidth=2)
        plt.axhline(y=equity_df['total_equity'].iloc[0], color='r', linestyle='--', alpha=0.5, label='Initial Capital')
        plt.fill_between(equity_df['date'], equity_df['total_equity'], equity_df['total_equity'].iloc[0], alpha=0.3)
        
        plt.title('Equity Curve', fontsize=16, fontweight='bold')
        plt.xlabel('Date')
        plt.ylabel('Capital (Rs.)')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            plt.savefig(output_path / 'equity_curve.png', dpi=300)
            logger.info(f"Equity curve saved to {output_path / 'equity_curve.png'}")
        
        plt.close()
    
    @staticmethod
    def plot_drawdown(equity_df: pd.DataFrame, output_dir: str = None):
        """Plot drawdown chart."""
        plt.figure(figsize=(12, 6))
        plt.fill_between(equity_df['date'], equity_df['drawdown'] * 100, 0, color='red', alpha=0.3)
        plt.plot(equity_df['date'], equity_df['drawdown'] * 100, color='red', linewidth=2)
        
        plt.title('Drawdown', fontsize=16, fontweight='bold')
        plt.xlabel('Date')
        plt.ylabel('Drawdown (%)')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            plt.savefig(output_path / 'drawdown.png', dpi=300)
            logger.info(f"Drawdown chart saved to {output_path / 'drawdown.png'}")
        
        plt.close()
    
    @staticmethod
    def plot_trade_distribution(trades_df: pd.DataFrame, output_dir: str = None):
        """Plot P&L distribution."""
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        # P&L histogram
        axes[0].hist(trades_df['pnl'], bins=30, edgecolor='black', alpha=0.7)
        axes[0].axvline(x=0, color='r', linestyle='--', linewidth=2)
        axes[0].set_title('Trade P&L Distribution')
        axes[0].set_xlabel('P&L (Rs.)')
        axes[0].set_ylabel('Frequency')
        axes[0].grid(True, alpha=0.3)
        
        # Cumulative P&L
        trades_df_sorted = trades_df.sort_values('exit_date')
        cumulative_pnl = trades_df_sorted['pnl'].cumsum()
        axes[1].plot(range(len(cumulative_pnl)), cumulative_pnl, linewidth=2)
        axes[1].axhline(y=0, color='r', linestyle='--', alpha=0.5)
        axes[1].set_title('Cumulative P&L')
        axes[1].set_xlabel('Trade Number')
        axes[1].set_ylabel('Cumulative P&L (Rs.)')
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            plt.savefig(output_path / 'trade_distribution.png', dpi=300)
            logger.info(f"Trade distribution saved to {output_path / 'trade_distribution.png'}")
        
        plt.close()
