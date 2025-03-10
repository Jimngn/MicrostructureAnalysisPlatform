import os
from typing import Dict, Any

class Config:
    # API settings
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    
    # Database settings
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_NAME = os.getenv("DB_NAME", "market_microstructure")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
    
    # Market data settings
    DEFAULT_SYMBOLS = ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA"]
    DEFAULT_TIMEFRAME = "1min"
    
    # Backtesting settings
    BACKTEST_WORKERS = int(os.getenv("BACKTEST_WORKERS", "4"))
    BACKTEST_DATA_DIR = os.getenv("BACKTEST_DATA_DIR", "./data/historical")
    
    # Toxic flow detection
    TOXIC_FLOW_THRESHOLD = float(os.getenv("TOXIC_FLOW_THRESHOLD", "0.7"))
    
    @classmethod
    def get_database_url(cls) -> str:
        return f"postgresql://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}" 