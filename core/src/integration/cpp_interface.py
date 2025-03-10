import ctypes
from typing import List, Dict, Tuple, Optional

class OrderBookInterface:
    def __init__(self, lib_path: str = "liborderbook.so"):
        """Interface to the C++ order book implementation"""
        self.lib = ctypes.CDLL(lib_path)
        
        # Configure function signatures
        self.lib.create_order_book.argtypes = [ctypes.c_char_p]
        self.lib.create_order_book.restype = ctypes.c_void_p
        
        self.lib.add_order.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_double, 
                                     ctypes.c_double, ctypes.c_bool, ctypes.c_longlong]
        
        self.lib.modify_order.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_double]
        
        self.lib.cancel_order.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        
        self.lib.get_best_bid.argtypes = [ctypes.c_void_p]
        self.lib.get_best_bid.restype = ctypes.c_double
        
        self.lib.get_best_ask.argtypes = [ctypes.c_void_p]
        self.lib.get_best_ask.restype = ctypes.c_double
        
        self.lib.get_mid_price.argtypes = [ctypes.c_void_p]
        self.lib.get_mid_price.restype = ctypes.c_double
        
        self.lib.get_spread.argtypes = [ctypes.c_void_p]
        self.lib.get_spread.restype = ctypes.c_double
        
        self.lib.get_order_imbalance.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self.lib.get_order_imbalance.restype = ctypes.c_double
        
        # Initialize order books for symbols
        self.order_books = {}
        
    def create_book(self, symbol: str) -> None:
        """Create a new order book for a symbol"""
        symbol_bytes = symbol.encode('utf-8')
        handle = self.lib.create_order_book(symbol_bytes)
        self.order_books[symbol] = handle
        
    def add_order(self, symbol: str, order_id: str, price: float, 
                 quantity: float, is_buy: bool, timestamp_ns: int) -> None:
        """Add a new order to the book"""
        handle = self.order_books.get(symbol)
        if handle is None:
            raise ValueError(f"No order book exists for symbol {symbol}")
            
        order_id_bytes = order_id.encode('utf-8')
        self.lib.add_order(handle, order_id_bytes, price, quantity, is_buy, timestamp_ns)
        
    def modify_order(self, symbol: str, order_id: str, new_quantity: float) -> None:
        """Modify an existing order's quantity"""
        handle = self.order_books.get(symbol)
        if handle is None:
            raise ValueError(f"No order book exists for symbol {symbol}")
            
        order_id_bytes = order_id.encode('utf-8')
        self.lib.modify_order(handle, order_id_bytes, new_quantity)
        
    def cancel_order(self, symbol: str, order_id: str) -> None:
        """Cancel an existing order"""
        handle = self.order_books.get(symbol)
        if handle is None:
            raise ValueError(f"No order book exists for symbol {symbol}")
            
        order_id_bytes = order_id.encode('utf-8')
        self.lib.cancel_order(handle, order_id_bytes)
        
    def get_best_prices(self, symbol: str) -> Tuple[float, float]:
        """Get best bid and ask prices"""
        handle = self.order_books.get(symbol)
        if handle is None:
            raise ValueError(f"No order book exists for symbol {symbol}")
            
        best_bid = self.lib.get_best_bid(handle)
        best_ask = self.lib.get_best_ask(handle)
        return best_bid, best_ask
        
    def get_order_book_snapshot(self, symbol: str, levels: int = 10) -> Dict:
        """Get a snapshot of the order book"""
        handle = self.order_books.get(symbol)
        if handle is None:
            raise ValueError(f"No order book exists for symbol {symbol}")
            
        # Get bid levels
        bid_levels = []
        for i in range(levels):
            price = self.lib.get_bid_level_price(handle, i)
            volume = self.lib.get_bid_level_volume(handle, i)
            if price > 0:
                bid_levels.append((price, volume))
                
        # Get ask levels
        ask_levels = []
        for i in range(levels):
            price = self.lib.get_ask_level_price(handle, i)
            volume = self.lib.get_ask_level_volume(handle, i)
            if price < float('inf'):
                ask_levels.append((price, volume))
                
        mid_price = self.lib.get_mid_price(handle)
        spread = self.lib.get_spread(handle)
        order_imbalance = self.lib.get_order_imbalance(handle, 5)
        
        return {
            "bid_levels": bid_levels,
            "ask_levels": ask_levels,
            "mid_price": mid_price,
            "spread": spread,
            "order_imbalance": order_imbalance
        } 