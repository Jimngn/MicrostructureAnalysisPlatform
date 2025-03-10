from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np

from backtesting.src.execution.execution_model import Order

class Portfolio:
    def __init__(self, initial_capital: float = 1000000.0, execution_model = None):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}
        self.orders = []
        self.active_orders = []
        self.execution_model = execution_model
        self.equity_curve = []
        self.trades = []
        
    def place_market_order(self, symbol: str, quantity: float, direction: str) -> Order:
        order = Order(
            symbol=symbol,
            order_type="MARKET",
            direction=direction,
            quantity=quantity
        )
        self.orders.append(order)
        self.active_orders.append(order)
        return order
        
    def place_limit_order(self, symbol: str, quantity: float, 
                         price: float, direction: str) -> Order:
        order = Order(
            symbol=symbol,
            order_type="LIMIT",
            direction=direction,
            quantity=quantity,
            price=price
        )
        self.orders.append(order)
        self.active_orders.append(order)
        return order
        
    def place_stop_order(self, symbol: str, quantity: float, 
                        stop_price: float, direction: str) -> Order:
        order = Order(
            symbol=symbol,
            order_type="STOP",
            direction=direction,
            quantity=quantity,
            stop_price=stop_price
        )
        self.orders.append(order)
        self.active_orders.append(order)
        return order
        
    def cancel_order(self, order: Order) -> bool:
        if order in self.active_orders:
            order.status = "CANCELLED"
            self.active_orders.remove(order)
            return True
        return False
        
    def get_position(self, symbol: str) -> float:
        return self.positions.get(symbol, 0.0)
        
    def mark_to_market(self, prices: Dict[str, float], timestamp: int) -> float:
        equity = self.cash
        
        for symbol, quantity in self.positions.items():
            if symbol in prices:
                equity += quantity * prices[symbol]
                
        self.equity_curve.append({"timestamp": timestamp, "equity": equity})
        return equity
        
    def process_fills(self):
        for order in list(self.active_orders):
            if order.status == "FILLED":
                symbol = order.symbol
                quantity = order.quantity if order.direction == "BUY" else -order.quantity
                
                self.positions[symbol] = self.positions.get(symbol, 0.0) + quantity
                
                if order.direction == "BUY":
                    self.cash -= order.quantity * order.average_fill_price
                else:
                    self.cash += order.quantity * order.average_fill_price
                    
                self.trades.append({
                    "symbol": symbol,
                    "direction": order.direction,
                    "quantity": order.quantity,
                    "price": order.average_fill_price,
                    "timestamp": order.execution_time
                })
                
                self.active_orders.remove(order)
                
    def get_equity(self) -> float:
        return self.equity_curve[-1]["equity"] if self.equity_curve else self.initial_capital

class Strategy(ABC):
    def __init__(self, symbols: List[str], parameters: Dict[str, Any] = None):
        self.symbols = symbols
        self.parameters = parameters or {}
        self.portfolio = None
        
    def set_portfolio(self, portfolio: Portfolio):
        self.portfolio = portfolio
        
    @abstractmethod
    def initialize(self):
        pass
        
    @abstractmethod
    def on_bar(self, timestamp: int, bar_data: Dict[str, Dict], portfolio: Portfolio):
        pass
        
    def on_order_filled(self, order: Order):
        pass
        
    def calculate_performance(self) -> Dict:
        if not self.portfolio or not self.portfolio.equity_curve:
            return {}
            
        equity_curve = pd.DataFrame(self.portfolio.equity_curve)
        equity_curve.set_index("timestamp", inplace=True)
        
        initial_equity = self.portfolio.initial_capital
        final_equity = self.portfolio.get_equity()
        
        total_return = (final_equity / initial_equity) - 1
        
        returns = equity_curve["equity"].pct_change().dropna()
        annualized_return = (1 + total_return) ** (252 / len(returns)) - 1
        
        volatility = returns.std() * np.sqrt(252)
        sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
        
        drawdowns = 1 - equity_curve["equity"] / equity_curve["equity"].cummax()
        max_drawdown = drawdowns.max()
        
        win_trades = sum(1 for trade in self.portfolio.trades if 
                       (trade["direction"] == "BUY" and trade["price"] < final_equity) or
                       (trade["direction"] == "SELL" and trade["price"] > final_equity))
                       
        total_trades = len(self.portfolio.trades)
        win_rate = win_trades / total_trades if total_trades > 0 else 0
        
        return {
            "total_return": total_return,
            "annualized_return": annualized_return,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "win_rate": win_rate,
            "total_trades": total_trades
        } 