from typing import Dict, List, Optional, Union, Tuple
import numpy as np
import pandas as pd

class Order:
    def __init__(self, symbol: str, order_type: str, direction: str, 
                 quantity: float, price: Optional[float] = None,
                 stop_price: Optional[float] = None,
                 time_in_force: str = "DAY"):
        self.symbol = symbol
        self.order_type = order_type
        self.direction = direction
        self.quantity = quantity
        self.price = price
        self.stop_price = stop_price
        self.time_in_force = time_in_force
        self.status = "OPEN"
        self.filled_quantity = 0.0
        self.average_fill_price = 0.0
        self.fills = []
        self.creation_time = None
        self.execution_time = None
        self.order_id = None
        
    def update_status(self, status: str):
        self.status = status
        
    def add_fill(self, quantity: float, price: float, timestamp: int):
        self.fills.append({"quantity": quantity, "price": price, "timestamp": timestamp})
        self.filled_quantity += quantity
        
        total_value = sum(fill["quantity"] * fill["price"] for fill in self.fills)
        self.average_fill_price = total_value / self.filled_quantity if self.filled_quantity > 0 else 0.0
        
        if abs(self.filled_quantity - self.quantity) < 1e-6:
            self.status = "FILLED"
            self.execution_time = timestamp
        elif self.filled_quantity > 0:
            self.status = "PARTIALLY_FILLED"

class ExecutionModel:
    def __init__(self, slippage_model: str = "fixed", 
                 slippage_factor: float = 0.0001,
                 market_impact_factor: float = 0.1,
                 fill_probability: float = 1.0,
                 latency_ms: int = 0):
        self.slippage_model = slippage_model
        self.slippage_factor = slippage_factor
        self.market_impact_factor = market_impact_factor
        self.fill_probability = fill_probability
        self.latency_ms = latency_ms
        
    def calculate_slippage(self, order: Order, market_price: float) -> float:
        direction_multiplier = 1.0 if order.direction == "BUY" else -1.0
        
        if self.slippage_model == "fixed":
            return market_price * self.slippage_factor * direction_multiplier
        elif self.slippage_model == "normal":
            return market_price * np.random.normal(0, self.slippage_factor) * direction_multiplier
        elif self.slippage_model == "proportional":
            impact = market_price * self.slippage_factor * np.sqrt(order.quantity) * direction_multiplier
            return impact
        return 0.0
        
    def calculate_market_impact(self, order: Order, market_data: Dict) -> float:
        if "order_book" not in market_data:
            return 0.0
            
        direction_multiplier = 1.0 if order.direction == "BUY" else -1.0
        order_book = market_data["order_book"]
        
        if order.direction == "BUY":
            levels = order_book["ask_levels"]
        else:
            levels = order_book["bid_levels"]
            
        if not levels:
            return 0.0
            
        remaining_quantity = order.quantity
        weighted_price = 0.0
        quantity_filled = 0.0
        
        for level in levels:
            level_price = level[0]
            level_quantity = level[1]
            
            fill_quantity = min(remaining_quantity, level_quantity)
            weighted_price += fill_quantity * level_price
            quantity_filled += fill_quantity
            remaining_quantity -= fill_quantity
            
            if remaining_quantity <= 0:
                break
                
        if quantity_filled > 0:
            average_price = weighted_price / quantity_filled
            market_price = market_data.get("mid_price", levels[0][0])
            impact = (average_price - market_price) * direction_multiplier
            return impact * self.market_impact_factor
            
        return 0.0
        
    def execute_market_order(self, order: Order, market_data: Dict, timestamp: int) -> bool:
        market_price = market_data.get("mid_price", 
                                     market_data.get("close", 
                                                  market_data.get("price", 0.0)))
        
        if market_price <= 0:
            return False
            
        if order.direction == "BUY":
            execution_price = market_price + self.calculate_slippage(order, market_price)
            execution_price += self.calculate_market_impact(order, market_data)
        else:
            execution_price = market_price - self.calculate_slippage(order, market_price)
            execution_price -= self.calculate_market_impact(order, market_data)
            
        if np.random.random() <= self.fill_probability:
            order.add_fill(order.quantity, execution_price, timestamp + self.latency_ms)
            return True
        return False
        
    def execute_limit_order(self, order: Order, market_data: Dict, timestamp: int) -> bool:
        if not order.price:
            return False
            
        market_price = market_data.get("mid_price", 
                                     market_data.get("close", 
                                                  market_data.get("price", 0.0)))
        
        if order.direction == "BUY" and market_price <= order.price:
            execution_price = min(order.price, market_price)
            if np.random.random() <= self.fill_probability:
                order.add_fill(order.quantity, execution_price, timestamp + self.latency_ms)
                return True
        elif order.direction == "SELL" and market_price >= order.price:
            execution_price = max(order.price, market_price)
            if np.random.random() <= self.fill_probability:
                order.add_fill(order.quantity, execution_price, timestamp + self.latency_ms)
                return True
                
        return False
        
    def execute_order(self, order: Order, market_data: Dict, timestamp: int) -> bool:
        if order.status not in ["OPEN", "PARTIALLY_FILLED"]:
            return False
            
        if order.order_type == "MARKET":
            return self.execute_market_order(order, market_data, timestamp)
        elif order.order_type == "LIMIT":
            return self.execute_limit_order(order, market_data, timestamp)
        elif order.order_type == "STOP":
            market_price = market_data.get("mid_price", market_data.get("close", 0.0))
            if ((order.direction == "BUY" and market_price >= order.stop_price) or
                (order.direction == "SELL" and market_price <= order.stop_price)):
                order.order_type = "MARKET"
                return self.execute_market_order(order, market_data, timestamp)
                
        return False 