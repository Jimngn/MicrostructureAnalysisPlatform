import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

class ToxicFlowDetector:
    def __init__(self, window_size: int = 100, update_frequency: int = 10):
        self.window_size = window_size
        self.update_frequency = update_frequency
        self.order_history = {}
        self.cancel_history = {}
        self.trade_history = {}
        self.imbalance_history = {}
        self.price_impact_history = {}
        self.volatility_history = {}
        self.metrics_history = {}
        self.toxic_scores = {}
        self.logger = logging.getLogger("ToxicFlowDetector")
        
    def process_order(self, symbol: str, timestamp: int, order_id: str, 
                     order_type: str, quantity: float, is_buy: bool, price: float):
        if symbol not in self.order_history:
            self.initialize_symbol(symbol)
            
        self.order_history[symbol].append({
            "timestamp": timestamp,
            "order_id": order_id,
            "order_type": order_type,
            "quantity": quantity,
            "is_buy": is_buy,
            "price": price
        })
        
        if len(self.order_history[symbol]) > self.window_size:
            self.order_history[symbol].pop(0)
            
        if len(self.order_history[symbol]) % self.update_frequency == 0:
            self.update_metrics(symbol, timestamp)
            
    def process_cancel(self, symbol: str, timestamp: int, order_id: str):
        if symbol not in self.cancel_history:
            self.initialize_symbol(symbol)
            
        self.cancel_history[symbol].append({
            "timestamp": timestamp,
            "order_id": order_id
        })
        
        if len(self.cancel_history[symbol]) > self.window_size:
            self.cancel_history[symbol].pop(0)
            
    def process_trade(self, symbol: str, timestamp: int, trade_id: str, 
                     price: float, quantity: float, is_buy: bool):
        if symbol not in self.trade_history:
            self.initialize_symbol(symbol)
            
        self.trade_history[symbol].append({
            "timestamp": timestamp,
            "trade_id": trade_id,
            "price": price,
            "quantity": quantity,
            "is_buy": is_buy
        })
        
        if len(self.trade_history[symbol]) > self.window_size:
            self.trade_history[symbol].pop(0)
            
        if len(self.trade_history[symbol]) % self.update_frequency == 0:
            self.update_metrics(symbol, timestamp)
            
    def process_order_book(self, symbol: str, timestamp: int, 
                          order_imbalance: float, mid_price: float, 
                          price_impact: float, volatility: float):
        if symbol not in self.imbalance_history:
            self.initialize_symbol(symbol)
            
        self.imbalance_history[symbol].append({
            "timestamp": timestamp,
            "value": order_imbalance
        })
        
        self.price_impact_history[symbol].append({
            "timestamp": timestamp,
            "value": price_impact
        })
        
        self.volatility_history[symbol].append({
            "timestamp": timestamp,
            "value": volatility
        })
        
        if len(self.imbalance_history[symbol]) > self.window_size:
            self.imbalance_history[symbol].pop(0)
            
        if len(self.price_impact_history[symbol]) > self.window_size:
            self.price_impact_history[symbol].pop(0)
            
        if len(self.volatility_history[symbol]) > self.window_size:
            self.volatility_history[symbol].pop(0)
            
        self.update_metrics(symbol, timestamp)
            
    def initialize_symbol(self, symbol: str):
        self.order_history[symbol] = []
        self.cancel_history[symbol] = []
        self.trade_history[symbol] = []
        self.imbalance_history[symbol] = []
        self.price_impact_history[symbol] = []
        self.volatility_history[symbol] = []
        self.metrics_history[symbol] = []
        self.toxic_scores[symbol] = {
            "timestamp": 0,
            "is_toxic": False,
            "confidence": 0.0,
            "factors": {}
        }
            
    def update_metrics(self, symbol: str, timestamp: int):
        metrics = {}
        
        metrics["timestamp"] = timestamp
        
        cancel_trade_ratio = self.calculate_cancel_trade_ratio(symbol)
        metrics["cancel_trade_ratio"] = cancel_trade_ratio
        
        order_flow_imbalance = self.calculate_order_flow_imbalance(symbol)
        metrics["order_flow_imbalance"] = order_flow_imbalance
        
        price_impact = self.calculate_price_impact(symbol)
        metrics["price_impact"] = price_impact
        
        volatility = self.calculate_volatility(symbol)
        metrics["volatility"] = volatility
        
        order_size_metrics = self.calculate_order_size_metrics(symbol)
        metrics.update(order_size_metrics)
        
        self.metrics_history[symbol].append(metrics)
        
        if len(self.metrics_history[symbol]) > self.window_size:
            self.metrics_history[symbol].pop(0)
            
        self.update_toxic_score(symbol, timestamp)
            
    def calculate_cancel_trade_ratio(self, symbol: str) -> float:
        if symbol not in self.cancel_history or symbol not in self.trade_history:
            return 0.0
            
        if not self.trade_history[symbol]:
            return 0.0 if not self.cancel_history[symbol] else 100.0
            
        cancel_count = len(self.cancel_history[symbol])
        trade_count = len(self.trade_history[symbol])
        
        return cancel_count / trade_count if trade_count > 0 else 0.0
        
    def calculate_order_flow_imbalance(self, symbol: str) -> float:
        if symbol not in self.order_history or not self.order_history[symbol]:
            return 0.0
            
        buy_volume = sum(order["quantity"] for order in self.order_history[symbol] 
                      if order["is_buy"])
        sell_volume = sum(order["quantity"] for order in self.order_history[symbol] 
                       if not order["is_buy"])
                       
        total_volume = buy_volume + sell_volume
        
        return (buy_volume - sell_volume) / total_volume if total_volume > 0 else 0.0
        
    def calculate_price_impact(self, symbol: str) -> float:
        if (symbol not in self.price_impact_history or 
            not self.price_impact_history[symbol]):
            return 0.0
            
        return np.mean([item["value"] for item in self.price_impact_history[symbol]])
        
    def calculate_volatility(self, symbol: str) -> float:
        if symbol not in self.volatility_history or not self.volatility_history[symbol]:
            return 0.0
            
        return np.mean([item["value"] for item in self.volatility_history[symbol]])
        
    def calculate_order_size_metrics(self, symbol: str) -> Dict:
        if symbol not in self.order_history or not self.order_history[symbol]:
            return {"avg_order_size": 0.0, "large_order_ratio": 0.0}
            
        order_sizes = [order["quantity"] for order in self.order_history[symbol]]
        avg_order_size = np.mean(order_sizes) if order_sizes else 0.0
        
        if not order_sizes or avg_order_size == 0.0:
            return {"avg_order_size": 0.0, "large_order_ratio": 0.0}
            
        large_orders = sum(1 for size in order_sizes if size > 2 * avg_order_size)
        large_order_ratio = large_orders / len(order_sizes) if order_sizes else 0.0
        
        return {
            "avg_order_size": avg_order_size,
            "large_order_ratio": large_order_ratio
        }
        
    def update_toxic_score(self, symbol: str, timestamp: int):
        if (symbol not in self.metrics_history or 
            not self.metrics_history[symbol]):
            return
            
        metrics = self.metrics_history[symbol][-1]
        
        factors = {}
        
        cancel_trade_score = min(1.0, metrics["cancel_trade_ratio"] / 10.0)
        factors["Cancel/Trade Ratio"] = cancel_trade_score
        
        imbalance_score = min(1.0, abs(metrics["order_flow_imbalance"]))
        factors["Order Imbalance"] = imbalance_score
        
        price_impact_score = min(1.0, metrics["price_impact"] / 0.0005)
        factors["Price Impact"] = price_impact_score
        
        volatility_score = min(1.0, metrics["volatility"] / 0.002)
        factors["Recent Volatility"] = volatility_score
        
        large_order_score = min(1.0, metrics["large_order_ratio"] * 2)
        factors["Large Orders"] = large_order_score
        
        weights = {
            "Cancel/Trade Ratio": 0.25,
            "Order Imbalance": 0.20,
            "Price Impact": 0.20,
            "Recent Volatility": 0.15,
            "Large Orders": 0.20
        }
        
        weighted_scores = [factors[k] * weights[k] for k in factors]
        total_score = sum(weighted_scores)
        
        is_toxic = total_score > 0.6
        confidence = total_score if is_toxic else 1.0 - total_score
        
        factors_list = [{"name": name, "contribution": score} for name, score in factors.items()]
        
        self.toxic_scores[symbol] = {
            "timestamp": timestamp,
            "is_toxic": is_toxic,
            "confidence": confidence,
            "factors": factors_list
        }
        
    def get_toxic_flow_status(self, symbol: str) -> Dict:
        if symbol not in self.toxic_scores:
            return {
                "symbol": symbol,
                "is_toxic": False,
                "confidence": 0.0,
                "timestamp": int(datetime.now().timestamp() * 1000),
                "factors": []
            }
            
        result = self.toxic_scores[symbol].copy()
        result["symbol"] = symbol
        return result 