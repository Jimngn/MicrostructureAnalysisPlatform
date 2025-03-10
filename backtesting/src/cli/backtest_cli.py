import argparse
import os
import json
import pandas as pd
import datetime
from typing import Dict, List, Optional

from backtesting.src.engine.backtest_engine import BacktestEngine
from backtesting.src.execution.execution_model import ExecutionModel
from backtesting.src.strategy.strategy_base import Strategy
from backtesting.src.strategy.order_flow_imbalance_strategy import OrderFlowImbalanceStrategy
from core.src.data.data_loader import MarketDataLoader
from dashboard.src.config import Config

def parse_args():
    parser = argparse.ArgumentParser(description='Market Microstructure Backtesting CLI')
    
    parser.add_argument('--strategy', type=str, required=True,
                      help='Strategy name to backtest')
                      
    parser.add_argument('--symbols', type=str, required=True,
                      help='Comma-separated list of symbols')
                      
    parser.add_argument('--start-date', type=str, required=True,
                      help='Start date (YYYY-MM-DD)')
                      
    parser.add_argument('--end-date', type=str, required=True,
                      help='End date (YYYY-MM-DD)')
                      
    parser.add_argument('--capital', type=float, default=1000000.0,
                      help='Initial capital')
                      
    parser.add_argument('--params', type=str, default='{}',
                      help='Strategy parameters as JSON string')
                      
    parser.add_argument('--output', type=str, default='./backtest_results.json',
                      help='Output file for results')
                      
    parser.add_argument('--data-dir', type=str, default=None,
                      help='Directory for market data (default: Config.BACKTEST_DATA_DIR)')
                      
    parser.add_argument('--slippage', type=float, default=0.0001,
                      help='Slippage model factor')
                      
    parser.add_argument('--market-impact', type=float, default=0.1,
                      help='Market impact model factor')
                      
    return parser.parse_args()

def get_strategy_class(strategy_name: str) -> Strategy:
    strategies = {
        'OrderFlowImbalanceStrategy': OrderFlowImbalanceStrategy,
    }
    
    if strategy_name not in strategies:
        raise ValueError(f"Strategy '{strategy_name}' not found. Available strategies: {list(strategies.keys())}")
        
    return strategies[strategy_name]

def run_backtest(args):
    symbols = [s.strip() for s in args.symbols.split(',')]
    
    strategy_params = json.loads(args.params)
    
    strategy_class = get_strategy_class(args.strategy)
    strategy = strategy_class(symbols=symbols, parameters=strategy_params)
    
    data_dir = args.data_dir or Config.BACKTEST_DATA_DIR
    data_loader = MarketDataLoader(data_dir=data_dir)
    
    market_data = {}
    for symbol in symbols:
        data = data_loader.prepare_backtest_data(
            symbol=symbol,
            start_date=args.start_date,
            end_date=args.end_date
        )
        market_data[symbol] = data['ohlcv']
    
    execution_model = ExecutionModel(
        slippage_factor=args.slippage,
        market_impact_factor=args.market_impact
    )
    
    backtest_engine = BacktestEngine(
        strategy=strategy,
        data=market_data,
        initial_capital=args.capital,
        execution_model=execution_model
    )
    
    results = backtest_engine.run()
    
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
        
    print(f"Backtest completed. Results saved to {args.output}")
    print_summary(results)
    
def print_summary(results: Dict):
    print("\n===== BACKTEST SUMMARY =====")
    print(f"Total Return: {results['total_return']:.2%}")
    print(f"Annualized Return: {results['annualized_return']:.2%}")
    print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
    print(f"Max Drawdown: {results['max_drawdown']:.2%}")
    print(f"Win Rate: {results['win_rate']:.2%}")
    print(f"Total Trades: {results['total_trades']}")
    print("============================\n")

if __name__ == "__main__":
    args = parse_args()
    run_backtest(args) 