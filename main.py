#!/usr/bin/env python3
"""
Main entry point for GapSignal trading system.
"""
import os
import sys
import time
import logging
import threading
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import config
from app.api.data_fetcher import DataFetcher
from app.core.data_processor import DataProcessor
from app.api.binance_client import BinanceClient
from app.web.app import app, get_processed_data
from app.utils.telegram_notifier import telegram_notifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gapsignal.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class GapSignalSystem:
    """Main system class for GapSignal."""

    def __init__(self):
        """Initialize the system."""
        self.config = config
        self.binance_client = None
        self.data_fetcher = None
        self.data_processor = None
        self.running = False
        self.background_thread = None

    def initialize(self) -> bool:
        """Initialize system components."""
        try:
            logger.info("Initializing GapSignal system...")

            # Initialize Binance client
            logger.info("Initializing Binance client...")
            self.binance_client = BinanceClient()

            # Test connection
            if not self.binance_client.test_connection():
                logger.error("Failed to connect to Binance API")
                return False

            # Initialize data fetcher
            logger.info("Initializing data fetcher...")
            self.data_fetcher = DataFetcher(self.binance_client)

            # Initialize data processor
            logger.info("Initializing data processor...")
            self.data_processor = DataProcessor(self.binance_client)

            # Pre-load initial data to avoid empty cache on first page load
            logger.info("Pre-loading initial data in background...")
            from app.web.app import get_processed_data
            import threading
            threading.Thread(target=get_processed_data, kwargs={'force_refresh': True}, daemon=True).start()

            logger.info("System initialization complete")

            # Send Telegram notification
            try:
                port = self.config.get('web_port', 6000)
                telegram_notifier.notify_system_start(port)
            except Exception as e:
                logger.warning(f"Failed to send Telegram startup notification: {e}")

            return True

        except Exception as e:
            logger.error(f"Failed to initialize system: {e}")
            return False

    def start_background_tasks(self):
        """Start background data refresh tasks."""
        if self.background_thread and self.background_thread.is_alive():
            logger.warning("Background thread already running")
            return

        self.running = True
        self.background_thread = threading.Thread(
            target=self._background_worker,
            daemon=True
        )
        self.background_thread.start()
        logger.info("Background tasks started")

    def _background_worker(self):
        """Background worker for periodic data updates."""
        refresh_interval = 300  # 5 minutes

        while self.running:
            try:
                logger.info("Running background data refresh...")
                start_time = time.time()

                # Refresh data cache
                get_processed_data(force_refresh=True)

                elapsed = time.time() - start_time
                logger.info(f"Background refresh completed in {elapsed:.2f} seconds")

                # Sleep until next refresh
                time.sleep(refresh_interval)

            except Exception as e:
                logger.error(f"Error in background worker: {e}")
                time.sleep(60)  # Wait a minute before retrying

    def stop(self):
        """Stop the system."""
        logger.info("Stopping GapSignal system...")
        self.running = False

        if self.background_thread:
            self.background_thread.join(timeout=10)
            logger.info("Background tasks stopped")

        logger.info("System stopped")

        # Send Telegram notification
        try:
            telegram_notifier.notify_system_stop()
        except Exception as e:
            logger.warning(f"Failed to send Telegram shutdown notification: {e}")

    def print_status(self):
        """Print system status."""
        print("\n" + "=" * 60)
        print("GapSignal Trading System")
        print("=" * 60)

        # Configuration
        print("\nConfiguration:")
        print(f"  Web Port: {self.config.get('web_port')}")
        print(f"  Volume Threshold: ${self.config.get('volume_threshold_usdt'):,} USDT")
        print(f"  Price Change Threshold: {self.config.get('price_change_threshold_percent')}%")
        print(f"  Default Interval: {self.config.get('default_kline_interval')}")
        print(f"  Signal Lookback: {self.config.get('signal_lookback_periods')} candles")

        # System status
        print("\nSystem Status:")
        if self.binance_client:
            print("  [OK] Binance client initialized")
        else:
            print("  [ERROR] Binance client not initialized")

        if self.data_fetcher:
            cache_stats = self.data_fetcher.get_cache_stats()
            print(f"  [OK] Data fetcher initialized ({cache_stats['valid_entries']} cache entries)")
        else:
            print("  [ERROR] Data fetcher not initialized")

        print(f"  [OK] Web server ready on port {self.config.get('web_port')}")

        print("\n" + "=" * 60)


def main():
    """Main function."""
    system = GapSignalSystem()

    # Initialize system
    if not system.initialize():
        logger.error("System initialization failed. Exiting.")
        sys.exit(1)

    # Print status
    system.print_status()

    # Start background tasks
    system.start_background_tasks()

    try:
        # Start web server
        port = system.config.get('web_port', 6000)
        host = '0.0.0.0'

        logger.info(f"Starting web server on {host}:{port}")
        print(f"\nWeb interface available at: http://localhost:{port}")
        print("Press Ctrl+C to stop\n")

        # Run Flask app
        app.run(host=host, port=port, debug=False, threaded=True)

    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"Error running web server: {e}")
    finally:
        system.stop()
        logger.info("Goodbye!")


if __name__ == '__main__':
    main()