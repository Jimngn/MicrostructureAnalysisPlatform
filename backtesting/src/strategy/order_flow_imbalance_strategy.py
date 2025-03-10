from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd

from backtesting.src.strategy.strategy_base import Strategy, Portfolio

class OrderFlowImbalanceStrategy(Strategy):
    def initialize(self):
        self.lookback_window = self.parameters.get('lookback_window', 20)
        self.entry_threshold = self.parameters.get('entry_threshold', 0.7)
        self.exit_threshold = self.parameters.get('exit_threshold', 0.3)
        self.position_size = self.parameters.get('position_size', 0.1)
        self.stop_loss = self.parameters.get('stop_loss', 0.02)
        
        self.imbalance_history = {symbol: [] for symbol in self.symbols}
        self.entry_prices = {}
        
    def on_bar(self, timestamp: int, bar_data: Dict[str, Dict], portfolio: Portfolio):
        for symbol in self.symbols:
            if symbol not in bar_data:
                continue
                
            data = bar_data[symbol]
            
            if 'order_imbalance' in data:
                imbalance = data['order_imbalance']
            elif 'order_book' in data:
                order_book = data['order_book']
                bid_volume = sum(level[1] for level in order_book.get('bid_levels', [])[:5])
                ask_volume = sum(level[1] for level in order_book.get('ask_levels', [])[:5])
                total_volume = bid_volume + ask_volume
                imbalance = (bid_volume - ask_volume) / total_volume if total_volume > 0 else 0
            else:
                continue
                
            self.imbalance_history[symbol].append(imbalance)
            
            if len(self.imbalance_history[symbol]) > self.lookback_window:
                self.imbalance_history[symbol].pop(0)
                
            if len(self.imbalance_history[symbol]) < self.lookback_window:
                continue
                
            current_position = portfolio.get_position(symbol)
            
            avg_imbalance = np.mean(self.imbalance_history[symbol])
            std_imbalance = np.std(self.imbalance_history[symbol])
            
            normalized_imbalance = (imbalance - avg_imbalance) / std_imbalance if std_imbalance > 0 else 0
            
            market_price = data.get('mid_price', data.get('close', data.get('price', 0.0)))
            
            if current_position == 0:
                if normalized_imbalance > self.entry_threshold:
                    position_value = portfolio.get_equity() * self.position_size
                    shares = position_value / market_price
                    portfolio.place_market_order(symbol, shares, "BUY")
                    self.entry_prices[symbol] = market_price
                    
                elif normalized_imbalance < -self.entry_threshold:
                    position_value = portfolio.get_equity() * self.position_size
                    shares = position_value / market_price
                    portfolio.place_market_order(symbol, shares, "SELL")
                    self.entry_prices[symbol] = market_price
                    
            elif current_position > 0:
                if normalized_imbalance < -self.exit_threshold:
                    portfolio.place_market_order(symbol, current_position, "SELL")
                    
                elif symbol in self.entry_prices and market_price < self.entry_prices[symbol] * (1 - self.stop_loss):
                    portfolio.place_market_order(symbol, current_position, "SELL")
                    
            elif current_position < 0:
                if normalized_imbalance > self.exit_threshold:
                    portfolio.place_market_order(symbol, abs(current_position), "BUY")
                    
                elif symbol in self.entry_prices and market_price > self.entry_prices[symbol] * (1 + self.stop_loss):
                    portfolio.place_market_order(symbol, abs(current_position), "BUY")
                    
            portfolio.process_fills() 