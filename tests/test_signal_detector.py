"""
Tests for signal_detector module.
"""
import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.signal_detector import SignalDetector


def test_signal_detector_initialization(test_config):
    """Test SignalDetector initialization."""
    detector = SignalDetector(test_config)
    assert detector.lookback_periods == test_config['signal_lookback_periods']
    assert detector.change_threshold == test_config['signal_cumulative_change_threshold_percent']


def test_is_strictly_increasing():
    """Test strictly increasing sequence detection."""
    detector = SignalDetector()

    assert detector._is_strictly_increasing([1, 2, 3, 4]) == True
    assert detector._is_strictly_increasing([1, 2, 2, 3]) == False  # Not strictly increasing
    assert detector._is_strictly_increasing([4, 3, 2, 1]) == False
    assert detector._is_strictly_increasing([1]) == True  # Single element


def test_is_strictly_decreasing():
    """Test strictly decreasing sequence detection."""
    detector = SignalDetector()

    assert detector._is_strictly_decreasing([4, 3, 2, 1]) == True
    assert detector._is_strictly_decreasing([4, 3, 3, 2]) == False  # Not strictly decreasing
    assert detector._is_strictly_decreasing([1, 2, 3, 4]) == False
    assert detector._is_strictly_decreasing([1]) == True  # Single element


def test_calculate_confidence():
    """Test confidence calculation."""
    detector = SignalDetector({'signal_cumulative_change_threshold_percent': 1.0})

    # Exactly at threshold = 0.5 confidence
    assert detector._calculate_confidence(1.0, 1.0) == 0.5

    # 50% above threshold = 0.75 confidence
    assert detector._calculate_confidence(1.5, 1.0) == 0.75

    # Double threshold = 1.0 confidence (max)
    assert detector._calculate_confidence(2.0, 1.0) == 1.0

    # Below threshold = 0.5 confidence (minimum)
    assert detector._calculate_confidence(0.5, 1.0) == 0.5


def test_detect_signal_no_data():
    """Test signal detection with insufficient data."""
    detector = SignalDetector({'signal_lookback_periods': 3})

    # Empty klines
    result = detector.detect_signal([])
    assert result['signal'] == 'none'
    assert result['confidence'] == 0.0

    # Not enough data for lookback
    klines = [[0, '100', '105', '95', '102', '1000']] * 2  # Only 2 candles
    result = detector.detect_signal(klines)
    assert result['signal'] == 'none'
    assert result['confidence'] == 0.0


def test_detect_buy_signal(mock_klines):
    """Test buy signal detection."""
    # Create clearly increasing pattern for last 3 candles
    detector = SignalDetector({
        'signal_lookback_periods': 3,
        'signal_cumulative_change_threshold_percent': 0.1
    })

    # Modify last 3 candles to create buy signal
    klines = mock_klines.copy()

    # Last 3 candles: strictly increasing lows, closes, highs
    # with cumulative change > threshold
    for i in range(-3, 0):
        idx = len(klines) + i
        base = 100 + i + 3  # Ensure increasing values

        klines[idx][1] = str(base)        # open
        klines[idx][2] = str(base + 2)    # high
        klines[idx][3] = str(base - 1)    # low
        klines[idx][4] = str(base + 1)    # close

    result = detector.detect_signal(klines)

    # Should detect buy signal
    assert result['signal'] == 'buy'
    assert result['confidence'] > 0.5
    assert result['cumulative_change'] > 0.1


def test_detect_sell_signal(mock_klines):
    """Test sell signal detection."""
    detector = SignalDetector({
        'signal_lookback_periods': 3,
        'signal_cumulative_change_threshold_percent': 0.1
    })

    # Modify last 3 candles to create sell signal
    klines = mock_klines.copy()

    # Last 3 candles: strictly decreasing lows, closes, highs
    # with cumulative change < -threshold
    for i in range(-3, 0):
        idx = len(klines) + i
        base = 100 - i - 3  # Ensure decreasing values

        klines[idx][1] = str(base)        # open
        klines[idx][2] = str(base - 1)    # high (decreasing)
        klines[idx][3] = str(base - 2)    # low (decreasing)
        klines[idx][4] = str(base - 1.5)  # close (decreasing)

    result = detector.detect_signal(klines)

    # Should detect sell signal
    assert result['signal'] == 'sell'
    assert result['confidence'] > 0.5
    assert result['cumulative_change'] < -0.1


def test_analyze_trend(mock_klines):
    """Test trend analysis."""
    detector = SignalDetector()

    # Mock EMA values for different periods
    ema_values = {
        20: 105.0,
        60: 103.0,
        120: 101.0,
        250: 100.0
    }

    result = detector.analyze_trend(mock_klines, ema_values)

    assert 'trend' in result
    assert 'ema_positions' in result
    assert 'price' in result

    # Check EMA positions structure
    for period, position_info in result['ema_positions'].items():
        assert 'value' in position_info
        assert 'diff_percent' in position_info
        assert 'position' in position_info


def test_detect_signals_batch():
    """Test batch signal detection."""
    detector = SignalDetector({'signal_lookback_periods': 2})

    # Create mock data for multiple symbols
    symbols_data = {
        'BTCUSDT': [
            [0, '100', '105', '95', '102', '1000'],
            [0, '102', '107', '101', '105', '1200'],
            [0, '105', '110', '104', '108', '1500']
        ],
        'ETHUSDT': [
            [0, '50', '55', '45', '52', '500'],
            [0, '52', '57', '51', '55', '600'],
            [0, '55', '60', '54', '58', '700']
        ]
    }

    results = detector.detect_signals_batch(symbols_data)

    assert 'BTCUSDT' in results
    assert 'ETHUSDT' in results

    for symbol, result in results.items():
        assert 'signal' in result
        assert 'confidence' in result
        assert 'cumulative_change' in result
        assert 'details' in result