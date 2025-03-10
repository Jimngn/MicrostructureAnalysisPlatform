import numpy as np
import pandas as pd
import datetime
from typing import Dict, List, Callable, Optional, Tuple, Union
import matplotlib.pyplot as plt
from dataclasses import dataclass

@dataclass
class Position:
    symbol: str
    quantity: float
    entry_price: float
    entry_time: pd.Timestamp
    exit_price: Optional[float] = None
    exit_time: Optional[pd.Timestamp] = None
    
    @property
    def is_open(self) -> bool:
        return self.exit_price is None
    
    @property
    def pnl(self) -> float:
        if not self.is_open and self.exit_price is not None:
            return (self.exit_price - self.entry_price) * self.quantity
        return 0.0
    
    def close(self, price: float, time: pd.Timestamp) -> None:
        self.exit_price = price
        self.exit_time = time

class ExecutionModel:
    def __init__(self, 
                 slippage_model: str = 'fixed',
                 slippage_param: float = 0.0001,
                 latency_ms: float = 10.0,
                 fill_probability: float = 1.0):
        self.slippage_model = slippage_model
        self.slippage_param = slippage_param
        self.latency_ms = latency_ms
        self.fill_probability = fill_probability
    
    def calculate_execution_price(self, 
                                symbol: str,
                                price: float, 
                                quantity: float,
                                is_buy: bool,
                                market_data: Optional[Dict] = None) -> Tuple[float, bool]:
        is_filled = np.random.random() <= self.fill_probability
        
        if not is_filled:
            return price, False
            
        slippage = 0.0
        
        if self.slippage_model == 'fixed':
            slippage = price * self.slippage_param
        elif self.slippage_model == 'percentage':
            slippage = price * self.slippage_param * (1.0 + np.log(1 + quantity/100))
        elif self.slippage_model == 'market_impact':
            if market_data and 'adv' in market_data:
                daily_volume = market_data['adv']
                normalized_size = quantity / daily_volume if daily_volume > 0 else 0.01
                slippage = price * self.slippage_param * np.sqrt(normalized_size)
            else:
                slippage = price * self.slippage_param
                
        execution_price = price + (slippage if is_buy else -slippage)
        
        return execution_price, True

class Strategy:
    def __init__(self, name: str):
        self.name = name
    
    def initialize(self) -> None:
        pass
    
    def on_bar(self, 
               timestamp: pd.Timestamp, 
               data: Dict[str, pd.DataFrame], 
               portfolio: 'Portfolio') -> None:
        pass

class Portfolio:
    def __init__(self, 
                 initial_capital: float = 1000000.0,
                 execution_model: Optional[ExecutionModel] = None):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: List[Position] = []
        self.open_positions: Dict[str, Position] = {}
        self.closed_positions: List[Position] = []
        self.execution_model = execution_model or ExecutionModel()
        
        self.equity_curve = []
        self.trade_history = []
    
    def buy(self, 
            symbol: str, 
            quantity: float, 
            price: float, 
            timestamp: pd.Timestamp,
            market_data: Optional[Dict] = None) -> bool:
        if self.cash < quantity * price:
            return False
        
        exec_price, is_filled = self.execution_model.calculate_execution_price(
            symbol, price, quantity, True, market_data
        )
        
        if not is_filled:
            return False
        
        position = Position(
            symbol=symbol,
            quantity=quantity,
            entry_price=exec_price,
            entry_time=timestamp
        )
        
        self.positions.append(position)
        self.open_positions[symbol] = position
        self.cash -= quantity * exec_price
        
        self.trade_history.append({
            'time': timestamp,
            'symbol': symbol,
            'action': 'BUY',
            'quantity': quantity,
            'price': exec_price,
            'cash': self.cash
        })
        
        return True
    
    def sell(self, 
             symbol: str, 
             quantity: float, 
             price: float, 
             timestamp: pd.Timestamp,
             market_data: Optional[Dict] = None) -> bool:
        if symbol not in self.open_positions:
            return False
        
        position = self.open_positions[symbol]
        
        if position.quantity < quantity:
            return False
        
        exec_price, is_filled = self.execution_model.calculate_execution_price(
            symbol, price, quantity, False, market_data
        )
        
        if not is_filled:
            return False
        
        position.close(exec_price, timestamp)
        self.closed_positions.append(position)
        del self.open_positions[symbol]
        
        self.cash += quantity * exec_price
        
        self.trade_history.append({
            'time': timestamp,
            'symbol': symbol,
            'action': 'SELL',
            'quantity': quantity,
            'price': exec_price,
            'cash': self.cash
        })
        
        return True
    
    def mark_to_market(self, prices: Dict[str, float], timestamp: pd.Timestamp) -> float:
        value = self.cash
        
        for symbol, position in self.open_positions.items():
            if symbol in prices:
                value += position.quantity * prices[symbol]
        
        self.equity_curve.append({
            'time': timestamp,
            'equity': value
        })
        
        return value
    
    def get_equity_curve(self) -> pd.DataFrame:
        return pd.DataFrame(self.equity_curve).set_index('time')
        
    def get_trade_history(self) -> pd.DataFrame:
        return pd.DataFrame(self.trade_history)

class BacktestEngine:
    def __init__(self, 
                 strategy: Strategy,
                 data: Dict[str, pd.DataFrame],
                 initial_capital: float = 1000000.0,
                 execution_model: Optional[ExecutionModel] = None):
        self.strategy = strategy
        self.data = data
        self.portfolio = Portfolio(
            initial_capital=initial_capital,
            execution_model=execution_model or ExecutionModel()
        )
        
        self._align_data()
    
    def _align_data(self) -> None:
        indices = []
        for df in self.data.values():
            indices.append(set(df.index))
        
        if indices:
            common_indices = set.intersection(*indices)
            common_indices = sorted(list(common_indices))
            
            for symbol, df in self.data.items():
                self.data[symbol] = df.loc[common_indices]
    
    def run(self) -> Dict:
        self.strategy.initialize()
        
        timestamps = sorted(list(next(iter(self.data.values())).index))
        
        for timestamp in timestamps:
            bar_data = {}
            prices = {}
            
            for symbol, df in self.data.items():
                if timestamp in df.index:
                    bar_data[symbol] = df.loc[timestamp].to_dict()
                    prices[symbol] = df.loc[timestamp]['close']
            
            self.strategy.on_bar(timestamp, bar_data, self.portfolio)
            
            self.portfolio.mark_to_market(prices, timestamp)
        
        return self.calculate_performance()
    
    def calculate_performance(self) -> Dict:
        equity_curve = self.portfolio.get_equity_curve()
        
        equity_curve['returns'] = equity_curve['equity'].pct_change()
        
        total_return = (equity_curve['equity'].iloc[-1] / self.portfolio.initial_capital) - 1
        annual_return = total_return / (len(equity_curve) / 252)
        
        daily_returns = equity_curve['returns'].dropna()
        sharpe_ratio = np.sqrt(252) * daily_returns.mean() / daily_returns.std() if len(daily_returns) > 1 else 0
        
        equity_curve['peak'] = equity_curve['equity'].cummax()
        equity_curve['drawdown'] = (equity_curve['equity'] / equity_curve['peak']) - 1
        max_drawdown = equity_curve['drawdown'].min()
        
        trades = self.portfolio.closed_positions
        winning_trades = [t for t in trades if t.pnl > 0]
        win_rate = len(winning_trades) / len(trades) if trades else 0
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'trades': len(trades)
        }
    
    def plot_equity_curve(self) -> None:
        equity_curve = self.portfolio.get_equity_curve()
        
        plt.figure(figsize=(12, 6))
        plt.plot(equity_curve.index, equity_curve['equity'])
        plt.title(f"Equity Curve - {self.strategy.name}")
        plt.xlabel("Date")
        plt.ylabel("Portfolio Value")
        plt.grid(True)
        plt.tight_layout()
        plt.show()
    
    def plot_drawdowns(self) -> None:
        equity_curve = self.portfolio.get_equity_curve()
        
        equity_curve['peak'] = equity_curve['equity'].cummax()
        equity_curve['drawdown'] = (equity_curve['equity'] / equity_curve['peak']) - 1
        
        plt.figure(figsize=(12, 6))
        plt.plot(equity_curve.index, equity_curve['drawdown'] * 100)
        plt.title(f"Drawdowns - {self.strategy.name}")
        plt.xlabel("Date")
        plt.ylabel("Drawdown (%)")
        plt.grid(True)
        plt.tight_layout()
        plt.show() 