"""
Binance API client wrapper.
"""
import os
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

from binance.client import Client
from binance.exceptions import BinanceAPIException
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class BinanceClient:
    """Wrapper for Binance API client."""

    def __init__(self):
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_API_SECRET')

        if not api_key or not api_secret:
            raise ValueError("BINANCE_API_KEY and BINANCE_API_SECRET must be set in .env file")

        self.client = Client(api_key, api_secret)
        self.test_connection()

    def test_connection(self) -> bool:
        """Test connection to Binance API."""
        try:
            self.client.get_account()
            print("Binance API connection successful")
            return True
        except BinanceAPIException as e:
            print(f"Binance API connection failed: {e}")
            return False

    def get_all_futures_symbols(self) -> List[str]:
        """Get all USDT-margined futures symbols."""
        try:
            exchange_info = self.client.futures_exchange_info()
            symbols = [
                symbol['symbol']
                for symbol in exchange_info['symbols']
                if symbol['quoteAsset'] == 'USDT' and symbol['contractType'] == 'PERPETUAL'
            ]
            return symbols
        except BinanceAPIException as e:
            print(f"Error fetching futures symbols: {e}")
            return []

    def get_futures_ticker_24h(self, symbol: str = None) -> List[Dict[str, Any]]:
        """
        Get 24hr ticker statistics for futures.
        If symbol is None, returns all symbols.
        """
        try:
            if symbol:
                ticker = self.client.futures_ticker(symbol=symbol)
                return [ticker]
            else:
                tickers = self.client.futures_ticker()
                return tickers
        except BinanceAPIException as e:
            print(f"Error fetching futures ticker: {e}")
            return []

    def get_klines(
        self,
        symbol: str,
        interval: str = '15m',
        limit: int = 100,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> List[List[Any]]:
        """
        Get Kline/candlestick data for a symbol.

        Returns list of:
        [
            open_time,
            open,
            high,
            low,
            close,
            volume,
            close_time,
            quote_asset_volume,
            number_of_trades,
            taker_buy_base_asset_volume,
            taker_buy_quote_asset_volume,
            ignore
        ]
        """
        try:
            klines = self.client.futures_klines(
                symbol=symbol,
                interval=interval,
                limit=limit,
                startTime=start_time,
                endTime=end_time
            )
            return klines
        except BinanceAPIException as e:
            print(f"Error fetching klines for {symbol}: {e}")
            return []

    def get_futures_depth(self, symbol: str, limit: int = 5) -> Dict[str, Any]:
        """Get order book depth for futures."""
        try:
            depth = self.client.futures_order_book(symbol=symbol, limit=limit)
            return depth
        except BinanceAPIException as e:
            print(f"Error fetching depth for {symbol}: {e}")
            return {}

    def get_account_balance(self) -> List[Dict[str, str]]:
        """Get futures account balance."""
        try:
            balance = self.client.futures_account_balance()
            return balance
        except BinanceAPIException as e:
            print(f"Error fetching account balance: {e}")
            return []

    def get_exchange_info(self) -> Dict[str, Any]:
        """Get futures exchange information."""
        try:
            info = self.client.futures_exchange_info()
            return info
        except BinanceAPIException as e:
            print(f"Error fetching exchange info: {e}")
            return {}