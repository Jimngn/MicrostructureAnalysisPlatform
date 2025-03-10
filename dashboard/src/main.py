import asyncio
import uvicorn
import logging
from datetime import datetime
import threading
import signal
import sys
import os

from dashboard.src.api.main import app
from dashboard.src.api.ws_server import WebsocketServer
from dashboard.src.config import Config
from core.src.database.db_service import DatabaseService
from core.src.integration.cpp_interface import OrderBookInterface
from core.src.market_data.feed_handler import MarketDataFeedHandler
from core.src.analysis.microstructure_metrics import MicrostructureAnalyzer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("market_microstructure.log")
    ]
)

logger = logging.getLogger("MarketMicrostructure")

class MarketMicrostructureApp:
    def __init__(self):
        self.running = False
        self.db_service = DatabaseService(Config.get_database_url())
        self.ws_server = WebsocketServer(host=Config.API_HOST, port=Config.API_PORT + 1)
        
        self.analyzer = MicrostructureAnalyzer(window_size=100)
        self.order_book_interface = OrderBookInterface()
        
        for symbol in Config.DEFAULT_SYMBOLS:
            self.order_book_interface.create_book(symbol)
            
        self.feed_handler = MarketDataFeedHandler(
            order_book_interface=self.order_book_interface,
            analyzer=self.analyzer
        )
        
        self.setup_signal_handlers()
        
    def setup_signal_handlers(self):
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
    def signal_handler(self, sig, frame):
        logger.info("Shutdown signal received, closing application...")
        self.shutdown()
        sys.exit(0)
        
    async def start(self):
        if self.running:
            return
            
        self.running = True
        logger.info("Starting Market Microstructure Analysis Platform")
        
        await self.ws_server.start()
        
        self.feed_handler.start()
        
        self.register_subscribers()
        
        logger.info("All services started successfully")
        
        while self.running:
            await asyncio.sleep(1)
            
    def register_subscribers(self):
        def order_book_callback(symbol, snapshot):
            self.db_service.insert_order_book_snapshot(
                symbol=symbol,
                timestamp=int(datetime.now().timestamp() * 1000),
                bid_levels=snapshot["bid_levels"],
                ask_levels=snapshot["ask_levels"],
                mid_price=snapshot["mid_price"],
                spread=snapshot["spread"],
                order_imbalance=snapshot["order_imbalance"]
            )
            
            asyncio.create_task(
                self.ws_server.broadcast(f"orderbook_{symbol}", snapshot)
            )
            
        def metrics_callback(symbol, metrics):
            metrics_dict = metrics.__dict__
            self.db_service.insert_market_metrics(
                symbol=symbol,
                timestamp=metrics.timestamp,
                metrics=metrics_dict
            )
            
            asyncio.create_task(
                self.ws_server.broadcast(f"metrics_{symbol}", metrics_dict)
            )
            
        self.feed_handler.subscribe_to_order_book(order_book_callback)
        self.feed_handler.subscribe_to_metrics(metrics_callback)
        
    def shutdown(self):
        logger.info("Shutting down Market Microstructure Analysis Platform")
        
        self.running = False
        
        self.feed_handler.stop()
        
        if self.ws_server:
            asyncio.create_task(self.ws_server.stop())
            
        self.db_service.close()
        
        logger.info("All services stopped successfully")

def run_fastapi():
    uvicorn.run(app, host=Config.API_HOST, port=Config.API_PORT)

async def main():
    app_instance = MarketMicrostructureApp()
    
    fastapi_thread = threading.Thread(target=run_fastapi, daemon=True)
    fastapi_thread.start()
    
    await app_instance.start()

if __name__ == "__main__":
    asyncio.run(main()) 