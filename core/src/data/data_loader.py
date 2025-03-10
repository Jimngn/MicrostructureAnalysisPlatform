import pandas as pd
import numpy as np
import os
import gzip
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Tuple

class MarketDataLoader:
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = data_dir
        
    def load_csv_data(self, symbol: str, start_date: str, end_date: str, 
                    timeframe: str = "1min") -> pd.DataFrame:
        filename = f"{self.data_dir}/{symbol}_{timeframe}.csv"
        
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Data file not found: {filename}")
            
        df = pd.read_csv(filename)
        
        if "timestamp" in df.columns:
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
        elif "datetime" in df.columns:
            df["datetime"] = pd.to_datetime(df["datetime"])
        else:
            df["datetime"] = pd.to_datetime(df.index)
            
        df.set_index("datetime", inplace=True)
        
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        
        filtered_df = df[(df.index >= start) & (df.index <= end)]
        
        if filtered_df.empty:
            raise ValueError(f"No data found for {symbol} between {start_date} and {end_date}")
            
        return filtered_df
        
    def load_parquet_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        filename = f"{self.data_dir}/{symbol}.parquet"
        
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Data file not found: {filename}")
            
        df = pd.read_parquet(filename)
        
        if "timestamp" in df.columns:
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
        elif "datetime" in df.columns:
            df["datetime"] = pd.to_datetime(df["datetime"])
        else:
            df["datetime"] = pd.to_datetime(df.index)
            
        df.set_index("datetime", inplace=True)
        
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        
        filtered_df = df[(df.index >= start) & (df.index <= end)]
        
        if filtered_df.empty:
            raise ValueError(f"No data found for {symbol} between {start_date} and {end_date}")
            
        return filtered_df
        
    def load_order_book_data(self, symbol: str, date: str) -> List[Dict]:
        date_obj = pd.to_datetime(date).strftime("%Y%m%d")
        filename = f"{self.data_dir}/orderbook/{symbol}_order_book_{date_obj}.json.gz"
        
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Order book data file not found: {filename}")
            
        with gzip.open(filename, 'rt') as f:
            data = json.load(f)
            
        return data
        
    def load_tick_data(self, symbol: str, date: str) -> pd.DataFrame:
        date_obj = pd.to_datetime(date).strftime("%Y%m%d")
        filename = f"{self.data_dir}/ticks/{symbol}_ticks_{date_obj}.csv.gz"
        
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Tick data file not found: {filename}")
            
        df = pd.read_csv(filename, compression='gzip')
        
        if "timestamp" in df.columns:
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
        else:
            df["datetime"] = pd.to_datetime(df.index)
            
        df.set_index("datetime", inplace=True)
        
        return df
        
    def generate_synthetic_data(self, symbol: str, start_date: str, end_date: str, 
                              timeframe: str = "1min", include_orderbook: bool = False) -> Dict:
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        
        if timeframe == "1min":
            periods = int((end - start).total_seconds() / 60) + 1
            freq = "1min"
        elif timeframe == "1h":
            periods = int((end - start).total_seconds() / 3600) + 1
            freq = "1h"
        elif timeframe == "1d":
            periods = (end - start).days + 1
            freq = "1d"
        else:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
            
        timestamps = pd.date_range(start=start, periods=periods, freq=freq)
        
        np.random.seed(42)
        
        initial_price = 100.0
        prices = [initial_price]
        
        for i in range(1, len(timestamps)):
            price_change = np.random.normal(0, 0.0015) 
            new_price = prices[-1] * (1 + price_change)
            prices.append(new_price)
            
        volumes = np.random.lognormal(10, 1, size=len(timestamps))
        
        highs = []
        lows = []
        
        for i, price in enumerate(prices):
            daily_volatility = price * 0.015
            high = price + np.random.uniform(0, daily_volatility)
            low = price - np.random.uniform(0, daily_volatility)
            
            if i > 0:
                high = max(high, prices[i])
                low = min(low, prices[i])
                
            highs.append(high)
            lows.append(low)
            
        df = pd.DataFrame({
            'timestamp': [int(ts.timestamp() * 1000) for ts in timestamps],
            'open': [prices[max(0, i-1)] for i in range(len(prices))],
            'high': highs,
            'low': lows,
            'close': prices,
            'volume': volumes
        })
        
        if include_orderbook:
            order_books = []
            
            for i, row in df.iterrows():
                mid_price = row['close']
                spread = mid_price * 0.0005 + np.random.uniform(0, mid_price * 0.0005)
                
                bid_price = mid_price - spread / 2
                ask_price = mid_price + spread / 2
                
                bids = []
                for j in range(10):
                    level_price = bid_price - j * (mid_price * 0.0001)
                    level_volume = 100 * np.exp(-0.3 * j) + np.random.uniform(0, 20)
                    bids.append([level_price, level_volume])
                
                asks = []
                for j in range(10):
                    level_price = ask_price + j * (mid_price * 0.0001)
                    level_volume = 100 * np.exp(-0.3 * j) + np.random.uniform(0, 20)
                    asks.append([level_price, level_volume])
                    
                order_books.append({
                    'timestamp': row['timestamp'],
                    'bids': bids,
                    'asks': asks,
                    'mid_price': mid_price,
                    'spread': spread
                })
                
            return {
                'ohlcv': df,
                'order_books': order_books
            }
            
        return {
            'ohlcv': df
        }
        
    def prepare_backtest_data(self, symbol: str, start_date: str, end_date: str) -> Dict:
        try:
            ohlcv_data = self.load_csv_data(symbol, start_date, end_date)
        except FileNotFoundError:
            synthetic_data = self.generate_synthetic_data(
                symbol, start_date, end_date, include_orderbook=True
            )
            ohlcv_data = synthetic_data['ohlcv']
            
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        order_books = []
        for date in dates:
            date_str = date.strftime("%Y-%m-%d")
            try:
                daily_order_books = self.load_order_book_data(symbol, date_str)
                order_books.extend(daily_order_books)
            except FileNotFoundError:
                continue
                
        if not order_books and 'order_books' in locals().get('synthetic_data', {}):
            order_books = synthetic_data['order_books']
            
        return {
            'ohlcv': ohlcv_data,
            'order_books': order_books
        } 