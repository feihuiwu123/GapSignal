"""
Pytest configuration for GapSignal tests.
"""
import os
import sys
import pytest
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Test configuration
TEST_CONFIG = {
    'volume_threshold_usdt': 1000,  # Low threshold for testing
    'price_change_threshold_percent': 0.1,
    'signal_lookback_periods': 2,
    'signal_cumulative_change_threshold_percent': 0.1,
    'ema_periods': [3, 5, 10]  # For testing
}


@pytest.fixture
def test_config():
    """Provide test configuration."""
    return TEST_CONFIG.copy()


@pytest.fixture
def mock_klines():
    """Provide mock kline data for testing."""
    # Simple mock data: 10 candles with slight upward trend
    import time
    base_time = int(time.time() * 1000) - 10 * 60000  # 10 minutes ago

    klines = []
    for i in range(10):
        open_price = 100.0 + i * 0.1
        close_price = 101.0 + i * 0.1
        high_price = 102.0 + i * 0.1
        low_price = 99.0 + i * 0.1
        volume = 1000.0 + i * 100

        klines.append([
            base_time + i * 60000,  # open_time (1 minute intervals)
            str(open_price),        # open
            str(high_price),        # high
            str(low_price),         # low
            str(close_price),       # close
            str(volume),            # volume
            base_time + (i + 1) * 60000 - 1,  # close_time
            str(volume * close_price),  # quote_asset_volume
            10,                     # number_of_trades
            str(volume * 0.5),      # taker_buy_base_asset_volume
            str(volume * close_price * 0.5),  # taker_buy_quote_asset_volume
            '0'                     # ignore
        ])

    return klines


@pytest.fixture
def mock_ticker_data():
    """Provide mock ticker data for testing."""
    return [
        {
            'symbol': 'BTCUSDT',
            'quoteVolume': '50000000.0',
            'priceChangePercent': '1.5',
            'lastPrice': '45000.0',
            'highPrice': '45500.0',
            'lowPrice': '44500.0',
            'volume': '1000.0',
            'count': 1000
        },
        {
            'symbol': 'ETHUSDT',
            'quoteVolume': '30000000.0',
            'priceChangePercent': '0.5',
            'lastPrice': '3000.0',
            'highPrice': '3050.0',
            'lowPrice': '2950.0',
            'volume': '5000.0',
            'count': 500
        }
    ]