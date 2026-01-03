"""
Technical indicator calculations for GapSignal system.
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional


class IndicatorCalculator:
    """Calculate technical indicators."""

    def __init__(self, config=None):
        """
        Initialize indicator calculator.

        Args:
            config: Configuration object or dict with indicator parameters
        """
        self.config = config or {}
        self.ema_periods = self.config.get('ema_periods', [20, 60, 120, 250])

    def calculate_ema(self, prices: List[float], period: int) -> List[float]:
        """
        Calculate Exponential Moving Average (EMA).

        Args:
            prices: List of closing prices
            period: EMA period

        Returns:
            List of EMA values (same length as prices, NaN for first period-1 values)
        """
        if len(prices) < period:
            return [np.nan] * len(prices)

        # Convert to pandas Series for EMA calculation
        series = pd.Series(prices)
        ema = series.ewm(span=period, adjust=False).mean()
        return ema.tolist()

    def calculate_multiple_emas(self, prices: List[float]) -> Dict[int, List[float]]:
        """
        Calculate multiple EMAs for configured periods.

        Args:
            prices: List of closing prices

        Returns:
            Dict with period -> list of EMA values
        """
        results = {}
        for period in self.ema_periods:
            results[period] = self.calculate_ema(prices, period)
        return results

    def calculate_ema_differences(self, current_price: float, ema_values: Dict[int, float]) -> Dict[int, float]:
        """
        Calculate percentage difference between current price and EMA values.

        Args:
            current_price: Current closing price
            ema_values: Dict with period -> EMA value

        Returns:
            Dict with period -> percentage difference
        """
        differences = {}
        for period, ema_value in ema_values.items():
            if ema_value and ema_value != 0:
                diff_percent = ((current_price - ema_value) / ema_value) * 100
                differences[period] = diff_percent
            else:
                differences[period] = 0.0
        return differences

    def calculate_latest_emas(self, prices: List[float]) -> Dict[int, float]:
        """
        Calculate latest EMA values for all periods.

        Args:
            prices: List of closing prices

        Returns:
            Dict with period -> latest EMA value
        """
        all_emas = self.calculate_multiple_emas(prices)
        latest_emas = {}
        for period, ema_values in all_emas.items():
            # Get the last non-NaN value
            valid_values = [v for v in ema_values if not np.isnan(v)]
            if valid_values:
                latest_emas[period] = valid_values[-1]
            else:
                latest_emas[period] = 0.0
        return latest_emas

    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """
        Calculate Relative Strength Index (RSI).

        Args:
            prices: List of closing prices
            period: RSI period (default 14)

        Returns:
            Latest RSI value
        """
        if len(prices) < period + 1:
            return 50.0  # Neutral value

        # Calculate price changes
        deltas = np.diff(prices)
        seed = deltas[:period]
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period

        if down == 0:
            return 100.0

        rs = up / down
        rsi = 100.0 - (100.0 / (1.0 + rs))

        # Calculate remaining
        for i in range(period, len(deltas)):
            delta = deltas[i]
            if delta > 0:
                up_val = delta
                down_val = 0.0
            else:
                up_val = 0.0
                down_val = -delta

            up = (up * (period - 1) + up_val) / period
            down = (down * (period - 1) + down_val) / period

            if down == 0:
                rsi = 100.0
            else:
                rs = up / down
                rsi = 100.0 - (100.0 / (1.0 + rs))

        return rsi

    def calculate_atr(self, high: List[float], low: List[float], close: List[float], period: int = 14) -> float:
        """
        Calculate Average True Range (ATR).

        Args:
            high: List of high prices
            low: List of low prices
            close: List of closing prices
            period: ATR period (default 14)

        Returns:
            Latest ATR value
        """
        if len(high) < period or len(low) < period or len(close) < period:
            return 0.0

        # Calculate true ranges
        tr_list = []
        for i in range(1, len(high)):
            hl = high[i] - low[i]
            hc = abs(high[i] - close[i-1])
            lc = abs(low[i] - close[i-1])
            tr = max(hl, hc, lc)
            tr_list.append(tr)

        # Calculate ATR using Wilder's smoothing
        atr = np.mean(tr_list[:period])
        for i in range(period, len(tr_list)):
            atr = (atr * (period - 1) + tr_list[i]) / period

        return atr

    def calculate_bollinger_bands(self, prices: List[float], period: int = 20, std_dev: float = 2.0
                                 ) -> Dict[str, float]:
        """
        Calculate Bollinger Bands.

        Args:
            prices: List of closing prices
            period: Moving average period (default 20)
            std_dev: Standard deviation multiplier (default 2.0)

        Returns:
            Dict with 'upper', 'middle', 'lower' band values
        """
        if len(prices) < period:
            return {'upper': 0.0, 'middle': 0.0, 'lower': 0.0}

        # Calculate SMA
        sma = np.mean(prices[-period:])

        # Calculate standard deviation
        std = np.std(prices[-period:])

        upper = sma + (std_dev * std)
        lower = sma - (std_dev * std)

        return {
            'upper': upper,
            'middle': sma,
            'lower': lower
        }

    def calculate_macd(self, prices: List[float], fast_period: int = 12, slow_period: int = 26,
                      signal_period: int = 9) -> Dict[str, float]:
        """
        Calculate MACD indicator.

        Args:
            prices: List of closing prices
            fast_period: Fast EMA period (default 12)
            slow_period: Slow EMA period (default 26)
            signal_period: Signal line period (default 9)

        Returns:
            Dict with 'macd', 'signal', 'histogram' values
        """
        if len(prices) < slow_period + signal_period:
            return {'macd': 0.0, 'signal': 0.0, 'histogram': 0.0}

        # Calculate EMAs
        fast_ema = self.calculate_ema(prices, fast_period)
        slow_ema = self.calculate_ema(prices, slow_period)

        # Get latest values
        fast_val = fast_ema[-1]
        slow_val = slow_ema[-1]

        if np.isnan(fast_val) or np.isnan(slow_val):
            return {'macd': 0.0, 'signal': 0.0, 'histogram': 0.0}

        macd = fast_val - slow_val

        # Calculate signal line (EMA of MACD)
        macd_prices = [fast_ema[i] - slow_ema[i] for i in range(len(prices))
                      if not np.isnan(fast_ema[i]) and not np.isnan(slow_ema[i])]
        signal = self.calculate_ema(macd_prices, signal_period)[-1] if macd_prices else 0.0

        histogram = macd - signal if not np.isnan(signal) else 0.0

        return {
            'macd': macd,
            'signal': signal,
            'histogram': histogram
        }