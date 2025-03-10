import unittest
import sys
import os
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.src.integration.cpp_interface import OrderBookInterface
from backtesting.src.execution.execution_model import Order, ExecutionModel
from core.src.analysis.toxic_flow_detector import ToxicFlowDetector

class TestOrderBook(unittest.TestCase):
    def setUp(self):
        self.order_book = OrderBookInterface()
        self.symbol = "AAPL"
        self.order_book.create_book(self.symbol)
        
    def test_add_order(self):
        order_id = "order1"
        price = 150.0
        quantity = 100
        is_buy = True
        
        self.order_book.add_order(self.symbol, order_id, price, quantity, is_buy)
        
        best_bid = self.order_book.get_best_bid(self.symbol)
        self.assertEqual(best_bid, price)
        
        order_count = self.order_book.get_order_count(self.symbol)
        self.assertEqual(order_count, 1)
        
    def test_cancel_order(self):
        order_id = "order2"
        price = 150.0
        quantity = 100
        is_buy = True
        
        self.order_book.add_order(self.symbol, order_id, price, quantity, is_buy)
        order_count_before = self.order_book.get_order_count(self.symbol)
        
        self.order_book.cancel_order(self.symbol, order_id)
        order_count_after = self.order_book.get_order_count(self.symbol)
        
        self.assertEqual(order_count_before - 1, order_count_after)
        
    def test_modify_order(self):
        order_id = "order3"
        price = 150.0
        quantity = 100
        is_buy = True
        
        self.order_book.add_order(self.symbol, order_id, price, quantity, is_buy)
        
        new_quantity = 200
        self.order_book.modify_order(self.symbol, order_id, new_quantity)
        
        order_info = self.order_book.get_order_info(self.symbol, order_id)
        self.assertEqual(order_info["quantity"], new_quantity)
        
    def test_get_order_book_snapshot(self):
        self.order_book.add_order(self.symbol, "bid1", 149.0, 100, True)
        self.order_book.add_order(self.symbol, "bid2", 148.0, 200, True)
        self.order_book.add_order(self.symbol, "ask1", 151.0, 150, False)
        self.order_book.add_order(self.symbol, "ask2", 152.0, 250, False)
        
        snapshot = self.order_book.get_order_book_snapshot(self.symbol)
        
        self.assertEqual(len(snapshot["bid_levels"]), 2)
        self.assertEqual(len(snapshot["ask_levels"]), 2)
        self.assertEqual(snapshot["mid_price"], 150.0)
        self.assertEqual(snapshot["spread"], 2.0)
        
    def test_order_imbalance(self):
        self.order_book.add_order(self.symbol, "bid1", 149.0, 300, True)
        self.order_book.add_order(self.symbol, "bid2", 148.0, 200, True)
        self.order_book.add_order(self.symbol, "ask1", 151.0, 100, False)
        self.order_book.add_order(self.symbol, "ask2", 152.0, 100, False)
        
        imbalance = self.order_book.get_order_imbalance(self.symbol, 5)
        
        self.assertTrue(imbalance > 0)
        
class TestExecutionModel(unittest.TestCase):
    def setUp(self):
        self.execution_model = ExecutionModel(
            slippage_model="fixed",
            slippage_factor=0.0001,
            market_impact_factor=0.1,
            fill_probability=1.0
        )
        
    def test_market_order_execution(self):
        order = Order(
            symbol="AAPL",
            order_type="MARKET",
            direction="BUY",
            quantity=100
        )
        
        market_data = {
            "mid_price": 150.0,
            "bid_price": 149.5,
            "ask_price": 150.5,
            "volume": 10000
        }
        
        timestamp = 1625097600000
        
        result = self.execution_model.execute_market_order(order, market_data, timestamp)
        
        self.assertTrue(result)
        self.assertEqual(order.status, "FILLED")
        self.assertEqual(order.filled_quantity, 100)
        self.assertGreaterEqual(order.average_fill_price, market_data["mid_price"])
        
    def test_limit_order_execution(self):
        order = Order(
            symbol="AAPL",
            order_type="LIMIT",
            direction="BUY",
            quantity=100,
            price=149.0
        )
        
        market_data = {
            "mid_price": 148.5,
            "bid_price": 148.0,
            "ask_price": 149.0,
            "volume": 10000
        }
        
        timestamp = 1625097600000
        
        result = self.execution_model.execute_limit_order(order, market_data, timestamp)
        
        self.assertTrue(result)
        self.assertEqual(order.status, "FILLED")
        self.assertEqual(order.filled_quantity, 100)
        self.assertLessEqual(order.average_fill_price, order.price)
        
class TestToxicFlowDetector(unittest.TestCase):
    def setUp(self):
        self.detector = ToxicFlowDetector(window_size=20)
        self.symbol = "AAPL"
        
    def test_toxic_flow_detection(self):
        timestamp = 1625097600000
        
        for i in range(30):
            self.detector.process_order(
                symbol=self.symbol,
                timestamp=timestamp + i * 1000,
                order_id=f"order{i}",
                order_type="LIMIT",
                quantity=100,
                is_buy=i % 2 == 0,
                price=150.0 + (i % 5) * 0.1
            )
            
            if i % 3 == 0:
                self.detector.process_cancel(
                    symbol=self.symbol,
                    timestamp=timestamp + i * 1000 + 500,
                    order_id=f"order{i}"
                )
                
            if i % 4 == 0:
                self.detector.process_trade(
                    symbol=self.symbol,
                    timestamp=timestamp + i * 1000 + 700,
                    trade_id=f"trade{i}",
                    price=150.0 + (i % 5) * 0.1,
                    quantity=50,
                    is_buy=i % 2 == 0
                )
                
            self.detector.process_order_book(
                symbol=self.symbol,
                timestamp=timestamp + i * 1000 + 900,
                order_imbalance=0.2 if i % 2 == 0 else -0.2,
                mid_price=150.0 + i * 0.01,
                price_impact=0.0001 * (i % 5),
                volatility=0.0005 * (1 + i % 3)
            )
            
        status = self.detector.get_toxic_flow_status(self.symbol)
        
        self.assertIn("is_toxic", status)
        self.assertIn("confidence", status)
        self.assertIn("factors", status)
        self.assertTrue(isinstance(status["is_toxic"], bool))
        self.assertTrue(0 <= status["confidence"] <= 1)
        self.assertTrue(len(status["factors"]) > 0)

if __name__ == "__main__":
    unittest.main() 