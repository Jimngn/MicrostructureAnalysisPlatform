import numpy as np
from typing import Dict, List, Optional, Tuple
import pandas as pd

class MarketImpactSimulator:
    def __init__(self, 
                price_impact_factor: float = 0.1,
                decay_factor: float = 0.95,
                spread_factor: float = 0.2,
                volatility_factor: float = 0.5,
                random_factor: float = 0.1):
        self.price_impact_factor = price_impact_factor
        self.decay_factor = decay_factor
        self.spread_factor = spread_factor
        self.volatility_factor = volatility_factor
        self.random_factor = random_factor
        self.impact_history = {}
        
    def clear_history(self, symbol: Optional[str] = None):
        if symbol:
            if symbol in self.impact_history:
                del self.impact_history[symbol]
        else:
            self.impact_history = {}
            
    def calculate_immediate_impact(self, 
                                 symbol: str, 
                                 order_quantity: float, 
                                 is_buy: bool, 
                                 market_data: Dict) -> float:
        mid_price = market_data.get("mid_price", 0.0)
        if mid_price <= 0:
            return 0.0
            
        order_book = market_data.get("order_book", {})
        spread = market_data.get("spread", 0.0)
        volatility = market_data.get("volatility", 0.0)
        
        volume = 0.0
        if is_buy and "ask_levels" in order_book:
            volume = sum(level[1] for level in order_book["ask_levels"][:5])
        elif not is_buy and "bid_levels" in order_book:
            volume = sum(level[1] for level in order_book["bid_levels"][:5])
            
        if volume <= 0:
            volume = order_quantity * 10
            
        order_size_ratio = min(1.0, order_quantity / volume)
        
        spread_impact = spread * self.spread_factor
        vol_impact = volatility * self.volatility_factor
        random_impact = mid_price * self.random_factor * np.random.normal()
        
        base_impact = mid_price * self.price_impact_factor * order_size_ratio
        
        total_impact = base_impact + spread_impact + vol_impact + random_impact
        
        direction = 1 if is_buy else -1
        impact = total_impact * direction
        
        return impact
        
    def apply_market_impact(self, 
                          symbol: str, 
                          order_quantity: float, 
                          is_buy: bool, 
                          market_data: Dict,
                          timestamp: int) -> Dict:
        if symbol not in self.impact_history:
            self.impact_history[symbol] = []
            
        immediate_impact = self.calculate_immediate_impact(symbol, order_quantity, is_buy, market_data)
        
        self.impact_history[symbol].append({
            "timestamp": timestamp,
            "impact": immediate_impact,
            "quantity": order_quantity,
            "is_buy": is_buy
        })
        
        updated_market_data = market_data.copy()
        
        mid_price = market_data.get("mid_price", 0.0)
        if mid_price > 0:
            updated_market_data["mid_price"] = mid_price + immediate_impact
            
            if "bid_levels" in market_data:
                updated_bid_levels = []
                for level in market_data["bid_levels"]:
                    updated_bid_levels.append((level[0] + immediate_impact, level[1]))
                updated_market_data["bid_levels"] = updated_bid_levels
                
            if "ask_levels" in market_data:
                updated_ask_levels = []
                for level in market_data["ask_levels"]:
                    updated_ask_levels.append((level[0] + immediate_impact, level[1]))
                updated_market_data["ask_levels"] = updated_ask_levels
                
        return updated_market_data
        
    def decay_impact(self, symbol: str, current_timestamp: int) -> float:
        if symbol not in self.impact_history:
            return 0.0
            
        total_impact = 0.0
        kept_impacts = []
        
        for impact_event in self.impact_history[symbol]:
            time_diff = current_timestamp - impact_event["timestamp"]
            decay = self.decay_factor ** (time_diff / 1000.0)
            
            if decay > 0.01:
                decayed_impact = impact_event["impact"] * decay
                total_impact += decayed_impact
                
                kept_impact = impact_event.copy()
                kept_impact["impact"] = decayed_impact
                kept_impacts.append(kept_impact)
                
        self.impact_history[symbol] = kept_impacts
        return total_impact
        
    def update_market_data(self, symbol: str, market_data: Dict, current_timestamp: int) -> Dict:
        total_impact = self.decay_impact(symbol, current_timestamp)
        
        if abs(total_impact) < 1e-6:
            return market_data
            
        updated_market_data = market_data.copy()
        
        mid_price = market_data.get("mid_price", 0.0)
        if mid_price > 0:
            updated_market_data["mid_price"] = mid_price + total_impact
            
            if "bid_levels" in market_data:
                updated_bid_levels = []
                for level in market_data["bid_levels"]:
                    updated_bid_levels.append((level[0] + total_impact, level[1]))
                updated_market_data["bid_levels"] = updated_bid_levels
                
            if "ask_levels" in market_data:
                updated_ask_levels = []
                for level in market_data["ask_levels"]:
                    updated_ask_levels.append((level[0] + total_impact, level[1]))
                updated_market_data["ask_levels"] = updated_ask_levels
                
        return updated_market_data 