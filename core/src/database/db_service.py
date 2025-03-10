import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
import json
import time

class DatabaseService:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.conn = None
        self.connect()
        
    def connect(self):
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(self.connection_string)
            
    def execute_query(self, query: str, params: Optional[Tuple] = None) -> List[Dict]:
        self.connect()
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            if cursor.description is not None:
                return cursor.fetchall()
            return []
            
    def execute_batch(self, query: str, params_list: List[Tuple]):
        self.connect()
        with self.conn.cursor() as cursor:
            cursor.executemany(query, params_list)
        self.conn.commit()
        
    def insert_order_book_snapshot(self, symbol: str, timestamp: int, bid_levels: List, ask_levels: List, 
                                  mid_price: float, spread: float, order_imbalance: float):
        query = """
        INSERT INTO order_book_snapshots 
        (symbol, timestamp, bid_levels, ask_levels, mid_price, spread, order_imbalance)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        self.execute_query(query, (
            symbol, 
            timestamp, 
            json.dumps(bid_levels), 
            json.dumps(ask_levels),
            mid_price,
            spread,
            order_imbalance
        ))
        self.conn.commit()
        
    def insert_market_metrics(self, symbol: str, timestamp: int, metrics: Dict[str, float]):
        query = """
        INSERT INTO market_metrics
        (symbol, timestamp, metrics)
        VALUES (%s, %s, %s)
        """
        self.execute_query(query, (symbol, timestamp, json.dumps(metrics)))
        self.conn.commit()
        
    def insert_trade(self, symbol: str, trade_id: str, timestamp: int, 
                    price: float, quantity: float, is_buy: bool):
        query = """
        INSERT INTO trades
        (symbol, trade_id, timestamp, price, quantity, is_buy)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        self.execute_query(query, (symbol, trade_id, timestamp, price, quantity, is_buy))
        self.conn.commit()
        
    def insert_backtest_result(self, strategy_name: str, symbol: str, 
                             start_date: str, end_date: str, 
                             performance_metrics: Dict, equity_curve: List):
        query = """
        INSERT INTO backtest_results
        (strategy_name, symbol, start_date, end_date, performance_metrics, equity_curve)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        self.execute_query(query, (
            strategy_name, 
            symbol, 
            start_date, 
            end_date, 
            json.dumps(performance_metrics), 
            json.dumps(equity_curve)
        ))
        self.conn.commit()
        
    def get_order_book_snapshot(self, symbol: str, timestamp: Optional[int] = None):
        if timestamp is None:
            query = """
            SELECT * FROM order_book_snapshots
            WHERE symbol = %s
            ORDER BY timestamp DESC
            LIMIT 1
            """
            results = self.execute_query(query, (symbol,))
        else:
            query = """
            SELECT * FROM order_book_snapshots
            WHERE symbol = %s AND timestamp = %s
            """
            results = self.execute_query(query, (symbol, timestamp))
            
        if not results:
            return None
            
        result = results[0]
        result['bid_levels'] = json.loads(result['bid_levels'])
        result['ask_levels'] = json.loads(result['ask_levels'])
        return result
        
    def get_market_metrics(self, symbol: str, start_time: int, end_time: int):
        query = """
        SELECT * FROM market_metrics
        WHERE symbol = %s AND timestamp BETWEEN %s AND %s
        ORDER BY timestamp
        """
        results = self.execute_query(query, (symbol, start_time, end_time))
        
        for result in results:
            result['metrics'] = json.loads(result['metrics'])
            
        return results
        
    def get_trades(self, symbol: str, start_time: int, end_time: int):
        query = """
        SELECT * FROM trades
        WHERE symbol = %s AND timestamp BETWEEN %s AND %s
        ORDER BY timestamp
        """
        return self.execute_query(query, (symbol, start_time, end_time))
        
    def get_backtest_results(self, strategy_name: Optional[str] = None, 
                           symbol: Optional[str] = None):
        conditions = []
        params = []
        
        if strategy_name:
            conditions.append("strategy_name = %s")
            params.append(strategy_name)
            
        if symbol:
            conditions.append("symbol = %s")
            params.append(symbol)
            
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = f"""
        SELECT * FROM backtest_results
        WHERE {where_clause}
        ORDER BY created_at DESC
        """
        
        results = self.execute_query(query, tuple(params))
        
        for result in results:
            result['performance_metrics'] = json.loads(result['performance_metrics'])
            result['equity_curve'] = json.loads(result['equity_curve'])
            
        return results
        
    def get_time_series(self, symbol: str, metric: str, start_time: int, end_time: int):
        query = """
        SELECT timestamp, metrics->>%s as value 
        FROM market_metrics
        WHERE symbol = %s AND timestamp BETWEEN %s AND %s
        ORDER BY timestamp
        """
        return self.execute_query(query, (metric, symbol, start_time, end_time))
        
    def load_historical_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        query = """
        SELECT timestamp, 
               metrics->>'mid_price' as price,
               metrics->>'bid_price' as bid,
               metrics->>'ask_price' as ask,
               metrics->>'volume' as volume,
               metrics->>'order_imbalance' as order_imbalance
        FROM market_metrics
        WHERE symbol = %s AND timestamp BETWEEN %s AND %s
        ORDER BY timestamp
        """
        results = self.execute_query(query, (symbol, start_date, end_date))
        return pd.DataFrame(results)
        
    def close(self):
        if self.conn and not self.conn.closed:
            self.conn.close() 