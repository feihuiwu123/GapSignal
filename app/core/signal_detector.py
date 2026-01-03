"""
Signal detection module for GapSignal system.
Detects buy/sell signals based on consecutive candle patterns.
"""
from typing import List, Dict, Any, Optional, Tuple
import numpy as np


class SignalDetector:
    """Detect buy/sell signals based on candle patterns."""

    def __init__(self, config=None):
        """
        Initialize signal detector.

        Args:
            config: Configuration object or dict with signal parameters
        """
        self.config = config or {}
        self.lookback_periods = self.config.get('signal_lookback_periods', 3)
        self.change_threshold = self.config.get('signal_cumulative_change_threshold_percent', 1.0)

    def detect_signal(self, klines: List[List[Any]]) -> Dict[str, Any]:
        """
        Detect buy/sell signal from kline data.

        Args:
            klines: List of kline data where each kline is:
                   [open_time, open, high, low, close, volume, ...]

        Returns:
            Dict with signal information:
            {
                'signal': 'buy', 'sell', or 'none',
                'confidence': float (0-1),
                'cumulative_change': float (percentage),
                'details': {
                    'low_sequence': bool,
                    'close_sequence': bool,
                    'high_sequence': bool
                }
            }
        """
        if len(klines) < self.lookback_periods:
            return {'signal': 'none', 'confidence': 0.0, 'cumulative_change': 0.0, 'details': {}}

        # Extract relevant data for last N candles
        recent_klines = klines[-self.lookback_periods:]

        # Convert to float arrays
        lows = [float(k[3]) for k in recent_klines]      # low price
        closes = [float(k[4]) for k in recent_klines]    # close price
        highs = [float(k[2]) for k in recent_klines]     # high price

        # Calculate cumulative change percentage
        start_close = closes[0]
        end_close = closes[-1]
        cumulative_change = ((end_close - start_close) / start_close) * 100

        # Check sequences
        low_increasing = self._is_strictly_increasing(lows)
        low_decreasing = self._is_strictly_decreasing(lows)

        close_increasing = self._is_strictly_increasing(closes)
        close_decreasing = self._is_strictly_decreasing(closes)

        high_increasing = self._is_strictly_increasing(highs)
        high_decreasing = self._is_strictly_decreasing(highs)

        # Determine signal
        signal = 'none'
        confidence = 0.0

        # Buy signal conditions
        if (cumulative_change > self.change_threshold and
                low_increasing and close_increasing and high_increasing):
            signal = 'buy'
            confidence = self._calculate_confidence(cumulative_change, self.change_threshold)

        # Sell signal conditions
        elif (cumulative_change < -self.change_threshold and
              low_decreasing and close_decreasing and high_decreasing):
            signal = 'sell'
            confidence = self._calculate_confidence(abs(cumulative_change), self.change_threshold)

        return {
            'signal': signal,
            'confidence': confidence,
            'cumulative_change': cumulative_change,
            'details': {
                'low_sequence': 'increasing' if low_increasing else 'decreasing' if low_decreasing else 'mixed',
                'close_sequence': 'increasing' if close_increasing else 'decreasing' if close_decreasing else 'mixed',
                'high_sequence': 'increasing' if high_increasing else 'decreasing' if high_decreasing else 'mixed',
                'lookback_periods': self.lookback_periods,
                'change_threshold': self.change_threshold
            }
        }

    def _is_strictly_increasing(self, values: List[float]) -> bool:
        """Check if values are strictly increasing."""
        return all(values[i] < values[i+1] for i in range(len(values)-1))

    def _is_strictly_decreasing(self, values: List[float]) -> bool:
        """Check if values are strictly decreasing."""
        return all(values[i] > values[i+1] for i in range(len(values)-1))

    def _calculate_confidence(self, change: float, threshold: float) -> float:
        """
        Calculate signal confidence based on how much change exceeds threshold.

        Args:
            change: Absolute percentage change
            threshold: Minimum threshold percentage

        Returns:
            Confidence score between 0.5 and 1.0
        """
        if change <= threshold:
            return 0.5
        # Confidence increases linearly from 0.5 to 1.0 as change goes from threshold to 2*threshold
        excess = min(change - threshold, threshold)
        return 0.5 + (excess / threshold) * 0.5

    def detect_signals_batch(self, symbols_data: Dict[str, List[List[Any]]]) -> Dict[str, Dict[str, Any]]:
        """
        Detect signals for multiple symbols.

        Args:
            symbols_data: Dict with symbol -> klines data

        Returns:
            Dict with symbol -> signal info
        """
        results = {}
        for symbol, klines in symbols_data.items():
            results[symbol] = self.detect_signal(klines)
        return results

    def analyze_trend(self, klines: List[List[Any]], ema_values: Dict[int, float]) -> Dict[str, Any]:
        """
        Analyze trend based on price position relative to EMAs.

        Args:
            klines: Kline data
            ema_values: Dict with period -> EMA value

        Returns:
            Trend analysis
        """
        if not klines:
            return {'trend': 'neutral', 'ema_positions': {}}

        latest_close = float(klines[-1][4])
        ema_positions = {}

        for period, ema_value in sorted(ema_values.items()):
            if ema_value == 0:
                continue
            diff_percent = ((latest_close - ema_value) / ema_value) * 100
            ema_positions[period] = {
                'value': ema_value,
                'diff_percent': diff_percent,
                'position': 'above' if diff_percent > 0 else 'below'
            }

        # Determine overall trend based on EMA alignment
        if len(ema_positions) >= 2:
            periods = sorted(ema_positions.keys())
            # Check if price is above all EMAs (bullish) or below all EMAs (bearish)
            all_above = all(ema_positions[p]['position'] == 'above' for p in periods)
            all_below = all(ema_positions[p]['position'] == 'below' for p in periods)

            if all_above:
                trend = 'strong_bullish'
            elif all_below:
                trend = 'strong_bearish'
            else:
                # Check if shorter EMAs are above longer EMAs (bullish alignment)
                ema_values_list = [(p, ema_positions[p]['value']) for p in periods]
                bullish_alignment = all(ema_values_list[i][1] > ema_values_list[i+1][1]
                                       for i in range(len(ema_values_list)-1))
                bearish_alignment = all(ema_values_list[i][1] < ema_values_list[i+1][1]
                                       for i in range(len(ema_values_list)-1))

                if bullish_alignment:
                    trend = 'bullish'
                elif bearish_alignment:
                    trend = 'bearish'
                else:
                    trend = 'neutral'
        else:
            trend = 'neutral'

        return {
            'trend': trend,
            'ema_positions': ema_positions,
            'price': latest_close
        }