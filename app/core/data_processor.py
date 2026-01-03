"""
Data processing and filtering module for GapSignal system.
"""
from typing import List, Dict, Any, Optional, Tuple
import time
import logging
from .config import config
from .signal_detector import SignalDetector
from .indicators import IndicatorCalculator

logger = logging.getLogger(__name__)


class DataProcessor:
    """Process and filter trading data."""

    def __init__(self, binance_client=None):
        """
        Initialize data processor.

        Args:
            binance_client: Binance API client instance
        """
        self.binance_client = binance_client
        self.config = config
        self.signal_detector = SignalDetector(config._config)
        self.indicator_calculator = IndicatorCalculator(config._config)

        # Configuration parameters
        self.volume_threshold = self.config.get('volume_threshold_usdt', 50000000)
        self.price_change_threshold = self.config.get('price_change_threshold_percent', 1.0)
        self.default_interval = self.config.get('default_kline_interval', '15m')
        self.kline_limit = 100  # Number of klines to fetch per symbol

    def filter_trading_pairs(self, ticker_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter trading pairs based on volume and price change thresholds.

        Args:
            ticker_data: List of 24hr ticker data from Binance

        Returns:
            List of filtered ticker data
        """
        filtered = []

        for ticker in ticker_data:
            try:
                symbol = ticker.get('symbol', '')
                quote_volume = float(ticker.get('quoteVolume', 0))
                price_change = float(ticker.get('priceChangePercent', 0))

                # Apply filters
                if (quote_volume >= self.volume_threshold and
                        abs(price_change) >= self.price_change_threshold):
                    filtered.append({
                        'symbol': symbol,
                        'quote_volume': quote_volume,
                        'price_change_percent': price_change,
                        'last_price': float(ticker.get('lastPrice', 0)),
                        'high_price': float(ticker.get('highPrice', 0)),
                        'low_price': float(ticker.get('lowPrice', 0)),
                        'volume': float(ticker.get('volume', 0)),
                        'trades': int(ticker.get('count', 0))
                    })

            except (ValueError, KeyError) as e:
                logger.warning(f"Error processing ticker {ticker.get('symbol', 'unknown')}: {e}")
                continue

        # Sort by volume descending
        filtered.sort(key=lambda x: x['quote_volume'], reverse=True)

        logger.info(f"Filtered {len(filtered)} symbols from {len(ticker_data)} total")
        return filtered

    def process_symbol(self, symbol: str, klines: List[List[Any]]) -> Dict[str, Any]:
        """
        Process data for a single symbol.

        Args:
            symbol: Trading pair symbol
            klines: Kline data for the symbol

        Returns:
            Processed symbol data
        """
        if not klines or len(klines) < 10:  # Need enough data for analysis
            return {
                'symbol': symbol,
                'error': 'Insufficient data',
                'signal': 'none',
                'confidence': 0.0
            }

        try:
            # Extract closing prices
            close_prices = [float(k[4]) for k in klines]

            # Calculate indicators
            latest_emas = self.indicator_calculator.calculate_latest_emas(close_prices)
            current_price = close_prices[-1]
            ema_differences = self.indicator_calculator.calculate_ema_differences(current_price, latest_emas)

            # Detect signals
            signal_info = self.signal_detector.detect_signal(klines)

            # Analyze trend
            trend_info = self.signal_detector.analyze_trend(klines, latest_emas)

            # Calculate additional metrics
            high_prices = [float(k[2]) for k in klines]
            low_prices = [float(k[3]) for k in klines]

            rsi = self.indicator_calculator.calculate_rsi(close_prices)
            atr = self.indicator_calculator.calculate_atr(high_prices, low_prices, close_prices)
            bb = self.indicator_calculator.calculate_bollinger_bands(close_prices)
            macd = self.indicator_calculator.calculate_macd(close_prices)

            return {
                'symbol': symbol,
                'current_price': current_price,
                'signal': signal_info['signal'],
                'confidence': signal_info['confidence'],
                'cumulative_change': signal_info['cumulative_change'],
                'signal_details': signal_info['details'],
                'ema_values': latest_emas,
                'ema_differences': ema_differences,
                'trend': trend_info['trend'],
                'trend_details': trend_info['ema_positions'],
                'rsi': rsi,
                'atr': atr,
                'bollinger_bands': bb,
                'macd': macd,
                'volume_24h': 0.0,  # Will be filled from ticker data
                'price_change_24h': 0.0,  # Will be filled from ticker data
                'timestamp': int(time.time())
            }

        except Exception as e:
            logger.error(f"Error processing symbol {symbol}: {e}")
            return {
                'symbol': symbol,
                'error': str(e),
                'signal': 'none',
                'confidence': 0.0
            }

    def process_multiple_symbols(self, symbols: List[str], ticker_data: List[Dict[str, Any]],
                                interval: str = None) -> List[Dict[str, Any]]:
        """
        Process multiple symbols in batch.

        Args:
            symbols: List of symbols to process
            ticker_data: 24hr ticker data for volume/price change info
            interval: Kline interval (default from config)

        Returns:
            List of processed symbol data
        """
        interval = interval or self.default_interval
        results = []

        # Create ticker lookup dictionary
        ticker_lookup = {t['symbol']: t for t in ticker_data}

        for i, symbol in enumerate(symbols):
            try:
                # Fetch kline data
                if self.binance_client:
                    klines = self.binance_client.get_klines(
                        symbol=symbol,
                        interval=interval,
                        limit=self.kline_limit
                    )
                else:
                    logger.warning(f"No binance client, skipping {symbol}")
                    continue

                # Process symbol
                result = self.process_symbol(symbol, klines)

                # Add ticker data if available
                if symbol in ticker_lookup:
                    ticker = ticker_lookup[symbol]
                    result['volume_24h'] = float(ticker.get('quoteVolume', 0))
                    result['price_change_24h'] = float(ticker.get('priceChangePercent', 0))

                results.append(result)

                # Rate limiting to avoid API bans
                if i < len(symbols) - 1:
                    time.sleep(0.1)  # 100ms between requests

            except Exception as e:
                logger.error(f"Error processing symbol {symbol}: {e}")
                continue

        # Sort by confidence descending
        results.sort(key=lambda x: x.get('confidence', 0), reverse=True)

        return results

    def filter_by_signal(self, processed_data: List[Dict[str, Any]],
                         min_confidence: float = 0.6) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Filter processed data by signal and confidence.

        Args:
            processed_data: List of processed symbol data
            min_confidence: Minimum confidence threshold

        Returns:
            Tuple of (buy_signals, sell_signals)
        """
        buy_signals = []
        sell_signals = []

        for data in processed_data:
            if data.get('signal') == 'buy' and data.get('confidence', 0) >= min_confidence:
                buy_signals.append(data)
            elif data.get('signal') == 'sell' and data.get('confidence', 0) >= min_confidence:
                sell_signals.append(data)

        # Sort by confidence
        buy_signals.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        sell_signals.sort(key=lambda x: x.get('confidence', 0), reverse=True)

        return buy_signals, sell_signals

    def generate_summary(self, processed_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate summary statistics from processed data.

        Args:
            processed_data: List of processed symbol data

        Returns:
            Summary statistics
        """
        total_symbols = len(processed_data)

        # Count signals
        buy_count = sum(1 for d in processed_data if d.get('signal') == 'buy')
        sell_count = sum(1 for d in processed_data if d.get('signal') == 'sell')

        # Average confidence
        buy_confidence_avg = (sum(d.get('confidence', 0) for d in processed_data if d.get('signal') == 'buy') /
                              buy_count if buy_count > 0 else 0)
        sell_confidence_avg = (sum(d.get('confidence', 0) for d in processed_data if d.get('signal') == 'sell') /
                               sell_count if sell_count > 0 else 0)

        # Volume statistics
        volumes = [d.get('volume_24h', 0) for d in processed_data if d.get('volume_24h')]
        avg_volume = sum(volumes) / len(volumes) if volumes else 0
        max_volume = max(volumes) if volumes else 0

        # Price change statistics
        price_changes = [d.get('price_change_24h', 0) for d in processed_data if d.get('price_change_24h')]
        avg_price_change = sum(price_changes) / len(price_changes) if price_changes else 0
        max_price_change = max(abs(p) for p in price_changes) if price_changes else 0

        return {
            'total_symbols': total_symbols,
            'buy_signals': buy_count,
            'sell_signals': sell_count,
            'buy_confidence_avg': buy_confidence_avg,
            'sell_confidence_avg': sell_confidence_avg,
            'avg_volume': avg_volume,
            'max_volume': max_volume,
            'avg_price_change': avg_price_change,
            'max_price_change': max_price_change,
            'timestamp': int(time.time())
        }