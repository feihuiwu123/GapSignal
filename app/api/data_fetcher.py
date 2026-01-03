"""
Data fetcher with caching for GapSignal system.
"""
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from .binance_client import BinanceClient
from app.core.config import config

logger = logging.getLogger(__name__)


class DataFetcher:
    """Fetch and cache data from Binance API."""

    def __init__(self, binance_client: BinanceClient = None):
        """
        Initialize data fetcher.

        Args:
            binance_client: Binance API client instance
        """
        self.binance_client = binance_client or BinanceClient()
        self.config = config

        # Cache configuration
        self.cache_duration = 300  # 5 minutes in seconds
        self.cache = {}

    def _get_cache_key(self, key_type: str, **kwargs) -> str:
        """Generate cache key."""
        parts = [key_type]
        for k, v in sorted(kwargs.items()):
            parts.append(f"{k}_{v}")
        return ":".join(parts)

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid."""
        if cache_key not in self.cache:
            return False

        cache_entry = self.cache[cache_key]
        cache_time = cache_entry.get('timestamp', 0)
        return time.time() - cache_time < self.cache_duration

    def _get_from_cache(self, cache_key: str) -> Any:
        """Get data from cache."""
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]['data']
        return None

    def _set_to_cache(self, cache_key: str, data: Any) -> None:
        """Store data in cache."""
        self.cache[cache_key] = {
            'data': data,
            'timestamp': time.time()
        }

    def get_all_futures_symbols(self, use_cache: bool = True) -> List[str]:
        """Get all USDT-margined futures symbols."""
        cache_key = self._get_cache_key('all_futures_symbols')

        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                logger.debug("Returning cached futures symbols")
                return cached

        symbols = self.binance_client.get_all_futures_symbols()

        if use_cache and symbols:
            self._set_to_cache(cache_key, symbols)

        return symbols

    def get_futures_ticker_24h(self, symbol: str = None, use_cache: bool = True) -> List[Dict[str, Any]]:
        """Get 24hr ticker statistics."""
        cache_key = self._get_cache_key('futures_ticker_24h', symbol=symbol or 'all')

        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                logger.debug(f"Returning cached ticker data for {symbol or 'all'}")
                return cached

        tickers = self.binance_client.get_futures_ticker_24h(symbol)

        if use_cache and tickers:
            self._set_to_cache(cache_key, tickers)

        return tickers

    def get_klines(self, symbol: str, interval: str = '15m', limit: int = 100,
                   use_cache: bool = True) -> List[List[Any]]:
        """Get Kline/candlestick data."""
        cache_key = self._get_cache_key('klines', symbol=symbol, interval=interval, limit=limit)

        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                logger.debug(f"Returning cached klines for {symbol} {interval}")
                return cached

        klines = self.binance_client.get_klines(
            symbol=symbol,
            interval=interval,
            limit=limit
        )

        if use_cache and klines:
            self._set_to_cache(cache_key, klines)

        return klines

    def get_filtered_symbols(self, use_cache: bool = True) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Get filtered symbols based on volume and price change thresholds.

        Returns:
            Tuple of (filtered_symbols, all_ticker_data)
        """
        cache_key = self._get_cache_key('filtered_symbols')

        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                logger.debug("Returning cached filtered symbols")
                return cached

        # Get all ticker data
        ticker_data = self.get_futures_ticker_24h(use_cache=use_cache)

        # Filter based on thresholds
        volume_threshold = self.config.get('volume_threshold_usdt', 50000000)
        price_change_threshold = self.config.get('price_change_threshold_percent', 1.0)

        filtered_symbols = []
        for ticker in ticker_data:
            try:
                symbol = ticker.get('symbol', '')
                quote_volume = float(ticker.get('quoteVolume', 0))
                price_change = float(ticker.get('priceChangePercent', 0))

                if (quote_volume >= volume_threshold and
                        abs(price_change) >= price_change_threshold):
                    filtered_symbols.append(ticker)

            except (ValueError, KeyError) as e:
                logger.warning(f"Error processing ticker {ticker.get('symbol', 'unknown')}: {e}")
                continue

        result = (filtered_symbols, ticker_data)

        if use_cache and filtered_symbols:
            self._set_to_cache(cache_key, result)

        logger.info(f"Filtered {len(filtered_symbols)} symbols from {len(ticker_data)} total")
        return result

    def get_symbol_data(self, symbol: str, interval: str = None, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get comprehensive data for a single symbol.

        Args:
            symbol: Trading pair symbol
            interval: Kline interval (default from config)
            use_cache: Whether to use cache

        Returns:
            Comprehensive symbol data
        """
        cache_key = self._get_cache_key('symbol_data', symbol=symbol, interval=interval or 'default')

        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                logger.debug(f"Returning cached symbol data for {symbol}")
                return cached

        interval = interval or self.config.get('default_kline_interval', '15m')

        # Get ticker data
        ticker_data = self.get_futures_ticker_24h(symbol=symbol, use_cache=use_cache)
        ticker = ticker_data[0] if ticker_data else {}

        # Get kline data
        klines = self.get_klines(symbol, interval, use_cache=use_cache)

        result = {
            'symbol': symbol,
            'ticker': ticker,
            'klines': klines,
            'interval': interval,
            'timestamp': int(time.time())
        }

        if use_cache:
            self._set_to_cache(cache_key, result)

        return result

    def get_multiple_symbols_data(self, symbols: List[str], interval: str = None,
                                  use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Get data for multiple symbols.

        Args:
            symbols: List of symbols
            interval: Kline interval
            use_cache: Whether to use cache

        Returns:
            List of symbol data
        """
        results = []
        interval = interval or self.config.get('default_kline_interval', '15m')

        for symbol in symbols:
            try:
                data = self.get_symbol_data(symbol, interval, use_cache)
                results.append(data)
                # Small delay to avoid rate limiting
                time.sleep(0.05)
            except Exception as e:
                logger.error(f"Error fetching data for {symbol}: {e}")
                continue

        return results

    def clear_cache(self, key_prefix: str = None) -> int:
        """
        Clear cache entries.

        Args:
            key_prefix: If provided, only clear entries with this prefix

        Returns:
            Number of cache entries cleared
        """
        if key_prefix is None:
            count = len(self.cache)
            self.cache.clear()
            logger.info(f"Cleared all {count} cache entries")
            return count

        # Clear only entries with prefix
        keys_to_remove = [k for k in self.cache.keys() if k.startswith(key_prefix)]
        for key in keys_to_remove:
            del self.cache[key]

        logger.info(f"Cleared {len(keys_to_remove)} cache entries with prefix '{key_prefix}'")
        return len(keys_to_remove)

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_entries = len(self.cache)
        now = time.time()

        # Count valid and expired entries
        valid_count = 0
        expired_count = 0
        for entry in self.cache.values():
            cache_time = entry.get('timestamp', 0)
            if now - cache_time < self.cache_duration:
                valid_count += 1
            else:
                expired_count += 1

        return {
            'total_entries': total_entries,
            'valid_entries': valid_count,
            'expired_entries': expired_count,
            'cache_duration_seconds': self.cache_duration,
            'memory_usage_kb': sum(len(str(v)) for v in self.cache.values()) / 1024
        }

    def test_connection(self) -> bool:
        """Test connection to Binance API."""
        try:
            return self.binance_client.test_connection()
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False