from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
import json
from pydantic import BaseModel
import datetime
from typing import Dict, List, Optional
import os

app = FastAPI(title="Market Microstructure Analysis Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class OrderBookLevel(BaseModel):
    price: float
    volume: float

class OrderBook(BaseModel):
    symbol: str
    timestamp: int
    bid_levels: List[OrderBookLevel]
    ask_levels: List[OrderBookLevel]
    mid_price: float
    spread: float
    order_imbalance: float

class MarketMetric(BaseModel):
    name: str
    value: float
    timestamp: int

class TimeSeriesPoint(BaseModel):
    timestamp: int
    value: float

class BacktestResult(BaseModel):
    strategy_name: str
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    trades: int
    equity_curve: List[TimeSeriesPoint]

def get_sample_order_book(symbol: str) -> OrderBook:
    now = int(datetime.datetime.now().timestamp() * 1000)
    
    mid_price = 100.0 + np.sin(now / 10000) * 5
    spread = 0.05 + np.random.random() * 0.1
    
    bid_price = mid_price - spread / 2
    ask_price = mid_price + spread / 2
    
    bid_levels = []
    for i in range(10):
        level_price = bid_price - i * 0.1
        level_volume = 100 * (10 - i) + np.random.random() * 50
        bid_levels.append(OrderBookLevel(price=level_price, volume=level_volume))
    
    ask_levels = []
    for i in range(10):
        level_price = ask_price + i * 0.1
        level_volume = 100 * (10 - i) + np.random.random() * 50
        ask_levels.append(OrderBookLevel(price=level_price, volume=level_volume))
    
    total_bid_volume = sum(level.volume for level in bid_levels[:5])
    total_ask_volume = sum(level.volume for level in ask_levels[:5])
    order_imbalance = (total_bid_volume - total_ask_volume) / (total_bid_volume + total_ask_volume) if (total_bid_volume + total_ask_volume) > 0 else 0
    
    return OrderBook(
        symbol=symbol,
        timestamp=now,
        bid_levels=bid_levels,
        ask_levels=ask_levels,
        mid_price=mid_price,
        spread=spread,
        order_imbalance=order_imbalance
    )

def get_sample_metrics(symbol: str) -> List[MarketMetric]:
    now = int(datetime.datetime.now().timestamp() * 1000)
    
    metrics = [
        MarketMetric(name="Order Flow Imbalance", value=np.random.random() * 2 - 1, timestamp=now),
        MarketMetric(name="Price Impact (bps)", value=np.random.random() * 5, timestamp=now),
        MarketMetric(name="Volatility (1min)", value=np.random.random() * 0.2, timestamp=now),
        MarketMetric(name="Trade-to-Cancel Ratio", value=0.05 + np.random.random() * 0.1, timestamp=now),
        MarketMetric(name="Bid-Ask Spread (bps)", value=5 + np.random.random() * 10, timestamp=now),
    ]
    
    return metrics

def get_sample_timeseries(symbol: str, metric: str, start_time: int, end_time: int) -> List[TimeSeriesPoint]:
    timestamps = np.linspace(start_time, end_time, 100, dtype=int)
    
    if metric == "order_im 