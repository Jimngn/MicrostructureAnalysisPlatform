# Market Microstructure Analysis Platform

A high-performance platform for analyzing financial market microstructure, order book dynamics, and testing trading strategies. Combines C++/Rust/Python components for optimal performance.

## Features

- Order book visualization and real-time analysis
- Market impact simulation and estimation
- Microstructure metrics calculation
- Strategy backtesting engine with execution models
- Toxic flow detection algorithm
- Historical data loading and simulation
- API and WebSocket interface for data access
- Interactive dashboards and visualizations

## Getting Started

# Clone the repository
git clone https://github.com/Jimngn/market-microstructure.git


Install dependencies
pip install -r requirements.txt


Initialize the database
python dashboard/src/api/db_init.py


Run the application
python dashboard/src/main.py


## Project Structure

- `core/` - Core implementation (C++/Rust/Python)
  - `src/orderbook/` - Limit order book implementation
  - `src/analysis/` - Market metrics and toxic flow detection
  - `src/database/` - Data storage and retrieval
  - `src/integration/` - Language bindings
  - `src/data/` - Historical data loading

- `backtesting/` - Strategy testing framework
  - `src/strategy/` - Strategy implementations
  - `src/execution/` - Order execution models
  - `src/cli/` - Command-line interface

- `dashboard/` - Web interface and API
  - `src/api/` - FastAPI implementation
  - `src/visualization/` - Chart generation
  - `src/config.py` - Configuration settings

- `deployment/` - Deployment configurations
  - `Dockerfile` - Container definition
  - `docker-compose.yml` - Multi-container setup

## Usage Examples

### Running a Backtest via CLI

```bash
python -m backtesting.src.cli.backtest_cli \
  --strategy OrderFlowImbalanceStrategy \
  --symbols AAPL,MSFT \
  --start-date 2023-01-01 \
  --end-date 2023-12-31 \
  --capital 1000000 \
  --params '{"window": 20, "threshold": 0.5}' \
  --output ./results/backtest_results.json
```

### Creating a Custom Strategy

```python
from backtesting.src.strategy.strategy_base import Strategy

class SimpleStrategy(Strategy):
    def initialize(self):
        self.window = 20
        self.threshold = 0.5
        
    def on_bar(self, timestamp, bar_data, portfolio):
        for symbol in self.symbols:
            if symbol in bar_data:
                imbalance = self.calculate_imbalance(symbol)
                if imbalance > self.threshold:
                    portfolio.enter_long(symbol, 100)
                elif imbalance < -self.threshold:
                    portfolio.enter_short(symbol, 100)
```

### Toxic Flow Detection

```python
from core.src.analysis.toxic_flow_detector import ToxicFlowDetector

detector = ToxicFlowDetector(window_size=100)
detector.process_order_book(symbol="AAPL", timestamp=1625097600000,
                           order_imbalance=0.75, mid_price=150.0,
                           price_impact=0.0003, volatility=0.0015)
                           
status = detector.get_toxic_flow_status("AAPL")
print(f"Is toxic: {status['is_toxic']}, Confidence: {status['confidence']:.2f}")
```

## Deployment

```bash
# Build and start containers
cd deployment
docker-compose up -d

# Access the dashboard
open http://localhost:8000
```

## Testing

```bash
# Run unit tests
python -m unittest discover tests
```
