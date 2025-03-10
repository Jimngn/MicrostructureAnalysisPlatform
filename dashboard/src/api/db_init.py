import psycopg2
import os
from dashboard.src.config import Config

def init_database():
    conn = psycopg2.connect(Config.get_database_url())
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_book_snapshots (
        id SERIAL PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        timestamp BIGINT NOT NULL,
        bid_levels JSONB NOT NULL,
        ask_levels JSONB NOT NULL,
        mid_price FLOAT NOT NULL,
        spread FLOAT NOT NULL,
        order_imbalance FLOAT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS market_metrics (
        id SERIAL PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        timestamp BIGINT NOT NULL,
        metrics JSONB NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id SERIAL PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        trade_id VARCHAR(50) NOT NULL,
        timestamp BIGINT NOT NULL,
        price FLOAT NOT NULL,
        quantity FLOAT NOT NULL,
        is_buy BOOLEAN NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS backtest_results (
        id SERIAL PRIMARY KEY,
        strategy_name VARCHAR(100) NOT NULL,
        symbol VARCHAR(20) NOT NULL,
        start_date VARCHAR(20) NOT NULL,
        end_date VARCHAR(20) NOT NULL,
        performance_metrics JSONB NOT NULL,
        equity_curve JSONB NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_order_book_snapshots_symbol_timestamp ON order_book_snapshots (symbol, timestamp);
    CREATE INDEX IF NOT EXISTS idx_market_metrics_symbol_timestamp ON market_metrics (symbol, timestamp);
    CREATE INDEX IF NOT EXISTS idx_trades_symbol_timestamp ON trades (symbol, timestamp);
    CREATE INDEX IF NOT EXISTS idx_backtest_results_strategy ON backtest_results (strategy_name);
    """)
    
    conn.commit()
    cursor.close()
    conn.close()

if __name__ == "__main__":
    init_database() 