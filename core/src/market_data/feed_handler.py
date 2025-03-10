import threading
import time
import queue
from typing import Dict, List, Callable, Optional
import logging

from core.src.integration.cpp_interface import OrderBookInterface
from core.src.analysis.microstructure_metrics import MicrostructureAnalyzer

class MarketDataFeedHandler:
    def __init__(self, 
                order_book_interface: OrderBookInterface,
                analyzer: MicrostructureAnalyzer):
        self.order_book = order_book_interface
        self.analyzer = analyzer
        
        # Message queues for different types of events
        self.order_queue = queue.Queue()
        self.trade_queue = queue.Queue()
        
        # Processing flag for threads
        self.is_running = False
        self.threads = []
        
        # Event subscribers
        self.order_book_subscribers = []
        self.metric_subscribers = []
        
        # Setup logging
        self.logger = logging.getLogger("MarketDataFeedHandler")
        
    def start(self):
        """Start the feed handler processing threads"""
        if self.is_running:
            return
            
        self.is_running = True
        
        # Create and start order processing thread
        order_thread = threading.Thread(target=self._process_orders, daemon=True)
        order_thread.start()
        self.threads.append(order_thread)
        
        # Create and start trade processing thread
        trade_thread = threading.Thread(target=self._process_trades, daemon=True)
        trade_thread.start()
        self.threads.append(trade_thread)
        
        self.logger.info("Market data feed handler started")
        
    def stop(self):
        """Stop all processing threads"""
        self.is_running = False
        
        for thread in self.threads:
            thread.join(timeout=2.0)
            
        self.logger.info("Market data feed handler stopped")
        
    def submit_order_event(self, 
                          symbol: str, 
                          event_type: str, 
                          order_id: str, 
                          price: Optional[float] = None,
                          quantity: Optional[float] = None,
                          is_buy: Optional[bool] = None,
                          timestamp_ns: Optional[int] = None):
        """Submit an order event to be processed"""
        if timestamp_ns is None:
            timestamp_ns = int(time.time() * 1e9)
            
        self.order_queue.put({
            "symbol": symbol,
            "event_type": event_type,
            "order_id": order_id,
            "price": price,
            "quantity": quantity,
            "is_buy": is_buy,
            "timestamp_ns": timestamp_ns
        })
        
    def submit_trade_event(self,
                          symbol: str,
                          trade_id: str,
                          price: float,
                          quantity: float,
                          is_buy: bool,
                          timestamp_ns: Optional[int] = None):
        """Submit a trade event to be processed"""
        if timestamp_ns is None:
            timestamp_ns = int(time.time() * 1e9)
            
        self.trade_queue.put({
            "symbol": symbol,
            "trade_id": trade_id,
            "price": price,
            "quantity": quantity,
            "is_buy": is_buy,
            "timestamp_ns": timestamp_ns
        })
        
    def subscribe_to_order_book(self, callback: Callable):
        """Subscribe to order book updates"""
        self.order_book_subscribers.append(callback)
        
    def subscribe_to_metrics(self, callback: Callable):
        """Subscribe to market metrics updates"""
        self.metric_subscribers.append(callback)
        
    def _process_orders(self):
        """Process order events from the queue"""
        while self.is_running:
            try:
                event = self.order_queue.get(timeout=0.1)
                
                symbol = event["symbol"]
                event_type = event["event_type"]
                order_id = event["order_id"]
                
                # Update the order book
                if event_type == "add":
                    self.order_book.add_order(
                        symbol, 
                        order_id, 
                        event["price"], 
                        event["quantity"], 
                        event["is_buy"],
                        event["timestamp_ns"]
                    )
                elif event_type == "modify":
                    self.order_book.modify_order(
                        symbol,
                        order_id,
                        event["quantity"]
                    )
                elif event_type == "cancel":
                    self.order_book.cancel_order(
                        symbol,
                        order_id
                    )
                
                # Process for analyzer
                self.analyzer.process_order(
                    symbol=symbol,
                    timestamp=event["timestamp_ns"],
                    order_id=order_id,
                    action=event_type,
                    price=event.get("price"),
                    quantity=event.get("quantity"),
                    is_buy=event.get("is_buy")
                )
                
                # Get current order book snapshot
                snapshot = self.order_book.get_order_book_snapshot(symbol)
                
                # Notify subscribers
                for callback in self.order_book_subscribers:
                    callback(symbol, snapshot)
                    
                self.order_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error processing order event: {str(e)}")
                
    def _process_trades(self):
        """Process trade events from the queue"""
        while self.is_running:
            try:
                event = self.trade_queue.get(timeout=0.1)
                
                symbol = event["symbol"]
                
                # Process for analyzer
                self.analyzer.process_trade(
                    symbol=symbol,
                    timestamp=event["timestamp_ns"],
                    price=event["price"],
                    quantity=event["quantity"],
                    is_buy=event["is_buy"]
                )
                
                # Get current order book snapshot
                snapshot = self.order_book.get_order_book_snapshot(symbol)
                
                # Process order book metrics
                metrics = self.analyzer.process_order_book(
                    symbol=symbol,
                    timestamp=event["timestamp_ns"],
                    bids=snapshot["bid_levels"],
                    asks=snapshot["ask_levels"]
                )
                
                # Notify subscribers
                for callback in self.metric_subscribers:
                    callback(symbol, metrics)
                    
                self.trade_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error processing trade event: {str(e)}") 