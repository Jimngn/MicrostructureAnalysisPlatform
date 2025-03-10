import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass

@dataclass
class MarketMetrics:
    symbol: str
    timestamp: int
    mid_price: float
    spread: float
    order_imbalance: float
    price_impact: float
    realized_volatility: float
    effective_spread: Optional[float] = None
    trade_to_cancel_ratio: Optional[float] = None
    liquidity_weight: Optional[float] = None

class MicrostructureAnalyzer:
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.metrics_history = {}
        self.order_history = {}
        self.trade_history = {}
        
    def process_order_book(self, 
                           symbol: str, 
                           timestamp: int, 
                           bids: List[Tuple[float, float]], 
                           asks: List[Tuple[float, float]]) -> MarketMetrics:
        if symbol not in self.metrics_history:
            self.metrics_history[symbol] = []
            self.order_history[symbol] = []
            self.trade_history[symbol] = []
        
        best_bid = bids[0][0] if bids else 0
        best_ask = asks[0][0] if asks else float('inf')
        mid_price = (best_bid + best_ask) / 2 if best_bid > 0 and best_ask < float('inf') else 0
        spread = best_ask - best_bid if best_bid > 0 and best_ask < float('inf') else 0
        
        bid_volume = sum([qty for _, qty in bids[:5]]) if len(bids) >= 5 else sum([qty for _, qty in bids])
        ask_volume = sum([qty for _, qty in asks[:5]]) if len(asks) >= 5 else sum([qty for _, qty in asks])
        total_volume = bid_volume + ask_volume
        order_imbalance = (bid_volume - ask_volume) / total_volume if total_volume > 0 else 0
        
        price_impact = self._calculate_price_impact(bids, asks)
        realized_volatility = self._calculate_realized_volatility(symbol, mid_price)
        
        metrics = MarketMetrics(
            symbol=symbol,
            timestamp=timestamp,
            mid_price=mid_price,
            spread=spread,
            order_imbalance=order_imbalance,
            price_impact=price_impact,
            realized_volatility=realized_volatility
        )
        
        self.metrics_history[symbol].append(metrics)
        if len(self.metrics_history[symbol]) > self.window_size:
            self.metrics_history[symbol].pop(0)
        
        return metrics
    
    def process_trade(self, 
                     symbol: str, 
                     timestamp: int, 
                     price: float, 
                     quantity: float, 
                     is_buy: bool) -> None:
        if symbol not in self.trade_history:
            self.trade_history[symbol] = []
        
        self.trade_history[symbol].append({
            'timestamp': timestamp,
            'price': price,
            'quantity': quantity,
            'is_buy': is_buy
        })
        
        if len(self.trade_history[symbol]) > self.window_size:
            self.trade_history[symbol].pop(0)
    
    def process_order(self,
                     symbol: str,
                     timestamp: int,
                     order_id: str,
                     action: str,
                     price: Optional[float] = None,
                     quantity: Optional[float] = None,
                     is_buy: Optional[bool] = None) -> None:
        if symbol not in self.order_history:
            self.order_history[symbol] = []
        
        self.order_history[symbol].append({
            'timestamp': timestamp,
            'order_id': order_id,
            'action': action,
            'price': price,
            'quantity': quantity,
            'is_buy': is_buy
        })
        
        if len(self.order_history[symbol]) > self.window_size:
            self.order_history[symbol].pop(0)
    
    def _calculate_price_impact(self, bids: List[Tuple[float, float]], asks: List[Tuple[float, float]]) -> float:
        if not bids or not asks:
            return 0.0
        
        best_bid = bids[0][0]
        best_ask = asks[0][0]
        mid_price = (best_bid + best_ask) / 2
        
        standard_size = 100  
        
        bid_impact = 0
        remaining = standard_size
        for price, qty in sorted(bids, key=lambda x: -x[0]):  
            filled = min(remaining, qty)
            bid_impact += filled * price
            remaining -= filled
            if remaining <= 0:
                break
        
        if remaining > 0:  
            bid_impact += remaining * best_bid * 0.95  
        
        bid_impact = bid_impact / standard_size if standard_size > 0 else 0
        
        ask_impact = 0
        remaining = standard_size
        for price, qty in sorted(asks, key=lambda x: x[0]):  
            filled = min(remaining, qty)
            ask_impact += filled * price
            remaining -= filled
            if remaining <= 0:
                break
        
        if remaining > 0:  
            ask_impact += remaining * best_ask * 1.05  
        
        ask_impact = ask_impact / standard_size if standard_size > 0 else 0
        
        price_impact = ((ask_impact - mid_price) + (mid_price - bid_impact)) / 2
        return price_impact / mid_price if mid_price > 0 else 0
    
    def _calculate_realized_volatility(self, symbol: str, current_price: float) -> float:
        if symbol not in self.metrics_history or len(self.metrics_history[symbol]) < 2:
            return 0.0
        
        prices = [m.mid_price for m in self.metrics_history[symbol]]
        prices.append(current_price)
        
        returns = np.diff(np.log(prices))
        return np.std(returns) * np.sqrt(252 * 6.5 * 60 * 60)  
    
    def calculate_trade_to_cancel_ratio(self, symbol: str, time_window_ms: int = 60000) -> float:
        if symbol not in self.trade_history or symbol not in self.order_history:
            return 0.0
        
        if not self.trade_history[symbol] or not self.order_history[symbol]:
            return 0.0
        
        latest_time = max(
            self.trade_history[symbol][-1]['timestamp'],
            self.order_history[symbol][-1]['timestamp']
        )
        
        start_time = latest_time - time_window_ms * 1000000  
        
        trades = [t for t in self.trade_history[symbol] if t['timestamp'] >= start_time]
        cancels = [o for o in self.order_history[symbol] if o['timestamp'] >= start_time and o['action'] == 'cancel']
        
        if not cancels:
            return float('inf')  
        
        return len(trades) / len(cancels)
    
    def detect_toxic_flow(self, symbol: str, threshold: float = 0.7) -> bool:
        if symbol not in self.metrics_history or len(self.metrics_history[symbol]) < 10:
            return False
        
        recent_metrics = self.metrics_history[symbol][-10:]
        
        order_imbalance_avg = np.mean([m.order_imbalance for m in recent_metrics])
        price_impact_avg = np.mean([m.price_impact for m in recent_metrics])
        volatility_avg = np.mean([m.realized_volatility for m in recent_metrics])
        
        imbalance_std = np.std([m.order_imbalance for m in recent_metrics])
        
        toxic_score = abs(order_imbalance_avg) * price_impact_avg * (1 + volatility_avg) * (1 + imbalance_std)
        
        return toxic_score > threshold
    
    def get_vwap(self, symbol: str, start_time: int, end_time: int) -> float:
        if symbol not in self.trade_history:
            return 0.0
        
        trades = [t for t in self.trade_history[symbol] 
                 if t['timestamp'] >= start_time and t['timestamp'] <= end_time]
        
        if not trades:
            return 0.0
        
        volume_total = sum(t['quantity'] for t in trades)
        if volume_total == 0:
            return 0.0
        
        weighted_sum = sum(t['price'] * t['quantity'] for t in trades)
        
        return weighted_sum / volume_total
    
    def get_historical_metrics(self, symbol: str, metric_name: str) -> List[Tuple[int, float]]:
        if symbol not in self.metrics_history:
            return []
        
        if metric_name == 'mid_price':
            return [(m.timestamp, m.mid_price) for m in self.metrics_history[symbol]]
        elif metric_name == 'spread':
            return [(m.timestamp, m.spread) for m in self.metrics_history[symbol]]
        elif metric_name == 'order_imbalance':
            return [(m.timestamp, m.order_imbalance) for m in self.metrics_history[symbol]]
        elif metric_name == 'price_impact':
            return [(m.timestamp, m.price_impact) for m in self.metrics_history[symbol]]
        elif metric_name == 'realized_volatility':
            return [(m.timestamp, m.realized_volatility) for m in self.metrics_history[symbol]]
        else:
            return [] 