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
    
    if metric == "order_imbalance":
        # Generate mean-reverting series
        values = np.random.normal(0, 0.3, 100)
        values = np.cumsum(values) * 0.1
        values = values - np.mean(values)
        values = np.clip(values, -1, 1)
    elif metric == "mid_price":
        # Generate random walk with drift
        values = np.cumsum(np.random.normal(0.0002, 0.002, 100))
        values = 100 * (1 + values)
    elif metric == "spread":
        # Generate positive series with spikes
        values = 0.05 + np.abs(np.random.normal(0, 0.02, 100))
        # Add occasional spikes
        for i in range(3):
            spike_idx = np.random.randint(0, 100)
            values[spike_idx] = values[spike_idx] * (3 + np.random.random() * 2)
    else:
        # Generic random series
        values = np.random.random(100)
    
    return [TimeSeriesPoint(timestamp=int(t), value=float(v)) for t, v in zip(timestamps, values)]

def get_sample_backtest_result(strategy_name: str) -> BacktestResult:
    days = 252
    timestamps = np.array([datetime.datetime.now() - datetime.timedelta(days=i) for i in range(days)])
    timestamps = [int(t.timestamp() * 1000) for t in reversed(timestamps)]
    
    # Generate equity curve with realistic properties
    daily_returns = np.random.normal(0.0005, 0.01, days)
    equity = 1000000 * np.cumprod(1 + daily_returns)
    
    equity_curve = [TimeSeriesPoint(timestamp=t, value=float(v)) for t, v in zip(timestamps, equity)]
    
    # Calculate performance metrics
    total_return = (equity[-1] / equity[0]) - 1
    annual_return = ((1 + total_return) ** (252 / days)) - 1
    sharpe_ratio = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252)
    
    # Calculate drawdowns
    peak = np.maximum.accumulate(equity)
    drawdown = (equity - peak) / peak
    max_drawdown = np.min(drawdown)
    
    # Simulate trades
    trades = int(days * (1 + np.random.random()))
    win_rate = 0.52 + np.random.random() * 0.1
    
    return BacktestResult(
        strategy_name=strategy_name,
        total_return=float(total_return),
        annual_return=float(annual_return),
        sharpe_ratio=float(sharpe_ratio),
        max_drawdown=float(max_drawdown),
        win_rate=float(win_rate),
        trades=trades,
        equity_curve=equity_curve
    )

# API Endpoints
@app.get("/api/symbols", response_model=List[str])
async def get_symbols():
    """Get list of available symbols"""
    return ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "NVDA", "JPM", "V", "PG"]

@app.get("/api/orderbook/{symbol}", response_model=OrderBook)
async def get_orderbook(symbol: str):
    """Get current order book for a symbol"""
    return get_sample_order_book(symbol)

@app.get("/api/metrics/{symbol}", response_model=List[MarketMetric])
async def get_metrics(symbol: str):
    """Get current market microstructure metrics for a symbol"""
    return get_sample_metrics(symbol)

@app.get("/api/timeseries/{symbol}/{metric}", response_model=List[TimeSeriesPoint])
async def get_metric_timeseries(
    symbol: str, 
    metric: str, 
    start_time: int = Query(..., description="Start timestamp in milliseconds"),
    end_time: int = Query(..., description="End timestamp in milliseconds")
):
    """Get historical time series data for a specific metric and symbol"""
    return get_sample_timeseries(symbol, metric, start_time, end_time)

@app.get("/api/strategies", response_model=List[str])
async def get_strategies():
    """Get list of available trading strategies"""
    return [
        "MomentumStrategy", 
        "MeanReversionStrategy", 
        "OrderFlowImbalanceStrategy",
        "VolatilityBreakoutStrategy",
        "LiquidityProviderStrategy"
    ]

@app.get("/api/backtest/{strategy}", response_model=BacktestResult)
async def get_backtest_results(
    strategy: str,
    symbol: str = Query(..., description="Symbol to run backtest on"),
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format")
):
    """Get backtest results for a specific strategy and timeframe"""
    return get_sample_backtest_result(strategy)

@app.post("/api/run_backtest")
async def run_backtest(strategy: str, symbol: str, start_date: str, end_date: str):
    """Run a backtest with specified parameters"""
    # In a real implementation, this would start an async task
    # For now, we'll just return success
    return {
        "status": "success", 
        "message": f"Started backtest for {strategy} on {symbol} from {start_date} to {end_date}",
        "job_id": "bt_" + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    }

@app.get("/api/toxic_flow_detection/{symbol}")
async def get_toxic_flow_status(symbol: str):
    """Check if current order flow is potentially toxic"""
    is_toxic = np.random.random() > 0.8  # 20% chance of being toxic
    confidence = 0.7 + np.random.random() * 0.3 if is_toxic else np.random.random() * 0.5
    
    return {
        "symbol": symbol,
        "is_toxic": is_toxic,
        "confidence": confidence,
        "timestamp": int(datetime.datetime.now().timestamp() * 1000),
        "factors": [
            {"name": "Order Imbalance", "contribution": np.random.random()},
            {"name": "Cancel/Trade Ratio", "contribution": np.random.random()},
            {"name": "Order Book Pressure", "contribution": np.random.random()},
            {"name": "Price Impact", "contribution": np.random.random()},
            {"name": "Recent Volatility", "contribution": np.random.random()}
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 