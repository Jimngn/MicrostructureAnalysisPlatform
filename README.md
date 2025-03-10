# Market Microstructure Analysis Platform

A tool for analyzing financial market microstructure, order book dynamics, and testing trading strategies. This platform combines high-performance components for order book management with analytical tools to understand market behavior at the microstructural level.

## Features

- Order book visualization and analysis
- Market impact simulation and estimation
- Real-time microstructure metrics calculation
- Strategy backtesting engine
- API and WebSocket interface for data access
- Toxic flow detection

## Getting Started

# Clone the repository
git clone https://github.com/yourusername/market-microstructure.git


Install dependencies
pip install -r requirements.txt


Initialize the database
python dashboard/src/api/db_init.py


Run the application
python dashboard/src/main.py


## Project Structure

- `core/` - Core implementation (C++/Rust/Python)
  - `src/orderbook/` - Limit order book implementation
  - `src/analysis/` - Market metrics calculation
  - `src/database/` - Data storage and retrieval
  - `src/integration/` - Language bindings

- `backtesting/` - Strategy testing framework
  - `src/strategy/` - Strategy implementations
  - `src/execution/` - Order execution models

- `dashboard/` - Web interface and API
  - `src/api/` - FastAPI implementation
  - `src/config.py` - Configuration settings

## Usage Example

python

Example strategy based on order flow imbalance


from backtesting.src.strategy.strategy_base import Strategy
class SimpleStrategy(Strategy):
def initialize(self):
self.window = 20
def on_bar(self, timestamp, bar_data, portfolio):
for symbol in self.symbols:
if symbol in bar_data:
# Trading logic here
pass