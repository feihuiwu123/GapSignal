"""
Tests for indicators module.
"""
import pytest
import numpy as np
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.indicators import IndicatorCalculator


def test_indicator_calculator_initialization(test_config):
    """Test IndicatorCalculator initialization."""
    calculator = IndicatorCalculator(test_config)
    assert calculator.ema_periods == test_config['ema_periods']


def test_calculate_ema():
    """Test EMA calculation."""
    calculator = IndicatorCalculator()

    # Simple test data
    prices = [100.0, 101.0, 102.0, 101.0, 100.0, 99.0, 100.0, 101.0, 102.0, 103.0]

    # Calculate EMA with period 3
    ema_values = calculator.calculate_ema(prices, 3)

    assert len(ema_values) == len(prices)

    # EMA values should all be valid numbers (pandas ewm may not return NaN)
    # Check that they're all floats and not NaN
    for value in ema_values:
        assert isinstance(value, float)
        # Check if value is not NaN (NaN != NaN)
        assert value == value  # NaN comparison returns False

    # EMA should be smoother than original prices (less variation)
    # Calculate variance of EMA vs original
    ema_variance = np.var(ema_values)
    price_variance = np.var(prices)
    # EMA should have lower or equal variance (smoother)
    assert ema_variance <= price_variance * 1.1  # Allow small tolerance


def test_calculate_multiple_emas():
    """Test multiple EMA calculation."""
    calculator = IndicatorCalculator({'ema_periods': [3, 5, 10]})

    prices = list(range(1, 21))  # 20 prices from 1 to 20

    results = calculator.calculate_multiple_emas(prices)

    assert len(results) == 3
    assert 3 in results
    assert 5 in results
    assert 10 in results

    for period, values in results.items():
        assert len(values) == len(prices)
        # Check that all values are valid (pandas ewm returns all values)
        for value in values:
            assert isinstance(value, float)
            # Check if value is not NaN (NaN != NaN)
            assert value == value

        # For EMA with adjust=False, early values are weighted differently
        # but still calculated. So we just verify we have the right number of values
        assert len(values) == len(prices)


def test_calculate_latest_emas():
    """Test latest EMA value calculation."""
    calculator = IndicatorCalculator({'ema_periods': [3, 5]})

    prices = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0]

    latest_emas = calculator.calculate_latest_emas(prices)

    assert len(latest_emas) == 2
    assert 3 in latest_emas
    assert 5 in latest_emas

    # Values should be numbers, not NaN
    assert not np.isnan(latest_emas[3])
    assert not np.isnan(latest_emas[5])


def test_calculate_ema_differences():
    """Test EMA difference calculation."""
    calculator = IndicatorCalculator()

    current_price = 105.0
    ema_values = {
        20: 100.0,
        60: 102.0,
        120: 104.0,
        250: 103.0
    }

    differences = calculator.calculate_ema_differences(current_price, ema_values)

    assert len(differences) == len(ema_values)
    assert 20 in differences
    assert 60 in differences
    assert 120 in differences
    assert 250 in differences

    # Price is above EMA20 by 5%, should be positive
    assert differences[20] == ((105.0 - 100.0) / 100.0) * 100

    # Test with zero EMA value (should return 0)
    differences_zero = calculator.calculate_ema_differences(current_price, {20: 0.0})
    assert differences_zero[20] == 0.0


def test_calculate_rsi():
    """Test RSI calculation."""
    calculator = IndicatorCalculator()

    # Create prices with clear upward trend
    prices = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0]

    rsi = calculator.calculate_rsi(prices, period=7)

    # RSI should be a float between 0 and 100
    assert isinstance(rsi, float)
    assert 0 <= rsi <= 100

    # With upward trend, RSI should be above 50
    assert rsi > 50

    # Test with insufficient data (should return neutral 50)
    short_prices = [100.0, 101.0]
    rsi_short = calculator.calculate_rsi(short_prices, period=14)
    assert rsi_short == 50.0


def test_calculate_atr():
    """Test ATR calculation."""
    calculator = IndicatorCalculator()

    # Create test data
    high = [105.0, 106.0, 107.0, 108.0, 109.0, 110.0]
    low = [95.0, 96.0, 97.0, 98.0, 99.0, 100.0]
    close = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]

    atr = calculator.calculate_atr(high, low, close, period=3)

    # ATR should be positive
    assert atr > 0

    # Test with insufficient data (should return 0)
    atr_short = calculator.calculate_atr(high[:2], low[:2], close[:2], period=3)
    assert atr_short == 0.0


def test_calculate_bollinger_bands():
    """Test Bollinger Bands calculation."""
    calculator = IndicatorCalculator()

    prices = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0]

    bb = calculator.calculate_bollinger_bands(prices, period=5, std_dev=2.0)

    assert 'upper' in bb
    assert 'middle' in bb
    assert 'lower' in bb

    # Middle band should be SMA of last period prices
    expected_sma = sum(prices[-5:]) / 5
    assert abs(bb['middle'] - expected_sma) < 0.001

    # Upper band should be higher than middle band
    assert bb['upper'] > bb['middle']

    # Lower band should be lower than middle band
    assert bb['lower'] < bb['middle']

    # Test with insufficient data (should return zeros)
    bb_short = calculator.calculate_bollinger_bands(prices[:3], period=5)
    assert bb_short['upper'] == 0.0
    assert bb_short['middle'] == 0.0
    assert bb_short['lower'] == 0.0


def test_calculate_macd():
    """Test MACD calculation."""
    calculator = IndicatorCalculator()

    # Create enough prices for MACD calculation (need at least slow_period + signal_period)
    prices = list(range(1, 51))  # 50 prices

    macd = calculator.calculate_macd(prices, fast_period=12, slow_period=26, signal_period=9)

    assert 'macd' in macd
    assert 'signal' in macd
    assert 'histogram' in macd

    # MACD line should be fast EMA - slow EMA
    # Since prices are increasing, MACD should be positive
    assert macd['macd'] > 0

    # Test with insufficient data (should return zeros)
    macd_short = calculator.calculate_macd(prices[:20], fast_period=12, slow_period=26, signal_period=9)
    assert macd_short['macd'] == 0.0
    assert macd_short['signal'] == 0.0
    assert macd_short['histogram'] == 0.0