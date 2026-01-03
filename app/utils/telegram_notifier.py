"""
Telegram notification module for GapSignal system.
"""
import os
import logging
from typing import Dict, Any, List, Optional
import requests
from dotenv import load_dotenv

load_dotenv()

from app.core.config import config

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Send notifications via Telegram bot."""

    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.enabled = bool(self.bot_token and self.chat_id)

        if self.enabled:
            # Test connection to verify token and permissions
            if self.test_connection():
                logger.info("Telegram notifier initialized and connected")
            else:
                logger.warning("Telegram notifier disabled - connection test failed")
                self.enabled = False
        else:
            logger.warning("Telegram notifier disabled - missing BOT_TOKEN or CHAT_ID")

    def send_message(self, text: str, parse_mode: str = 'HTML', disable_web_page_preview: bool = True) -> bool:
        """
        Send a message via Telegram bot.

        Args:
            text: Message text
            parse_mode: Parse mode (HTML or Markdown)
            disable_web_page_preview: Disable link previews

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("Telegram notifier disabled, message not sent")
            return False

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': parse_mode,
                'disable_web_page_preview': disable_web_page_preview
            }

            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()

            logger.debug(f"Telegram message sent: {text[:100]}...")
            return True

        except requests.exceptions.HTTPError as e:
            # Try to get more details from response
            try:
                if e.response is not None:
                    status_code = e.response.status_code
                    error_details = e.response.json()
                    error_desc = error_details.get('description', 'No description')
                    logger.error(f"Telegram API error ({status_code}): {error_desc}")

                    # Provide user-friendly guidance based on status code
                    if status_code == 400:
                        logger.error("Bad request. Check message format or chat_id.")
                    elif status_code == 401:
                        logger.error("Invalid bot token. Please check TELEGRAM_BOT_TOKEN in .env file.")
                    elif status_code == 403:
                        logger.error("Bot cannot send messages to this chat. Possible reasons:")
                        logger.error("1. Bot was blocked by the user")
                        logger.error("2. Chat ID is incorrect")
                        logger.error("3. Bot needs to be added to the group/channel first")
                        logger.error("4. User needs to send /start to the bot first")
                    elif status_code == 404:
                        logger.error("Chat not found. Please verify TELEGRAM_CHAT_ID.")
                    elif status_code == 429:
                        logger.error("Rate limit exceeded. Telegram limits: 30 messages/second.")
                else:
                    logger.error(f"Telegram HTTP error: {e}")
            except (ValueError, KeyError):
                logger.error(f"Telegram HTTP error: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    def format_signal_message(self, signal_data: Dict[str, Any], signal_type: str = 'buy') -> str:
        """
        Format signal data into a Telegram message.

        Args:
            signal_data: Signal data dictionary
            signal_type: 'buy' or 'sell'

        Returns:
            Formatted message string
        """
        port = config.get('web_port', 9000)
        symbol = signal_data.get('symbol', 'Unknown')
        current_price = signal_data.get('current_price', 0)
        confidence = signal_data.get('confidence', 0) * 100  # Convert to percentage
        cumulative_change = signal_data.get('cumulative_change', 0)
        volume_24h = signal_data.get('volume_24h', 0)

        ema_differences = signal_data.get('ema_differences', {})
        ema_diffs_str = " | ".join([f"EMA{period}: {diff:.2f}%"
                                   for period, diff in ema_differences.items()])

        signal_icon = "🟢" if signal_type == 'buy' else "🔴"
        signal_text = "BUY" if signal_type == 'buy' else "SELL"

        message = f"""
{signal_icon} <b>{signal_text} SIGNAL DETECTED</b>
━━━━━━━━━━━━━━━━━━━━
<b>Symbol:</b> {symbol}
<b>Price:</b> ${current_price:,.4f}
<b>Confidence:</b> {confidence:.1f}%
<b>Cumulative Change:</b> {cumulative_change:.2f}%
<b>24h Volume:</b> ${volume_24h:,.0f}

<b>EMA Differences:</b>
{ema_diffs_str}

<b>Other Indicators:</b>
RSI: {signal_data.get('rsi', 0):.1f}
ATR: {signal_data.get('atr', 0):.4f}
Trend: {signal_data.get('trend', 'neutral')}

<b>Links:</b>
• <a href="https://www.binance.com/en/futures/{symbol}">Binance Futures</a>
• <a href="http://localhost:{port}/detail/{symbol}">View Details</a>
        """

        return message.strip()

    def format_summary_message(self, summary: Dict[str, Any], processed_count: int) -> str:
        """
        Format summary data into a Telegram message.

        Args:
            summary: Summary statistics
            processed_count: Number of symbols processed

        Returns:
            Formatted message string
        """
        buy_count = summary.get('buy_signals', 0)
        sell_count = summary.get('sell_signals', 0)
        avg_volume = summary.get('avg_volume', 0)

        message = f"""
📊 <b>GapSignal Daily Summary</b>
━━━━━━━━━━━━━━━━━━━━
<b>Symbols Processed:</b> {processed_count}
<b>Buy Signals:</b> {buy_count}
<b>Sell Signals:</b> {sell_count}
<b>Avg 24h Volume:</b> ${avg_volume:,.0f}

<b>Signal Confidence:</b>
• Buy: {summary.get('buy_confidence_avg', 0)*100:.1f}%
• Sell: {summary.get('sell_confidence_avg', 0)*100:.1f}%

<b>Market Stats:</b>
• Max Volume: ${summary.get('max_volume', 0):,.0f}
• Avg Price Change: {summary.get('avg_price_change', 0):.2f}%
• Max Price Change: {summary.get('max_price_change', 0):.2f}%

<b>Status:</b> {'✅ Active' if buy_count > 0 or sell_count > 0 else '⏸️ Quiet'}
        """

        return message.strip()

    def notify_signal(self, signal_data: Dict[str, Any], signal_type: str = 'buy') -> bool:
        """
        Send notification for a new signal.

        Args:
            signal_data: Signal data dictionary
            signal_type: 'buy' or 'sell'

        Returns:
            True if notification sent successfully
        """
        message = self.format_signal_message(signal_data, signal_type)
        return self.send_message(message)

    def notify_summary(self, summary: Dict[str, Any], processed_count: int) -> bool:
        """
        Send daily summary notification.

        Args:
            summary: Summary statistics
            processed_count: Number of symbols processed

        Returns:
            True if notification sent successfully
        """
        message = self.format_summary_message(summary, processed_count)
        return self.send_message(message)

    def notify_error(self, error_message: str, context: str = "") -> bool:
        """
        Send error notification.

        Args:
            error_message: Error description
            context: Additional context

        Returns:
            True if notification sent successfully
        """
        message = f"""
🚨 <b>GapSignal Error Alert</b>
━━━━━━━━━━━━━━━━━━━━
<b>Error:</b> {error_message}
<b>Context:</b> {context if context else 'General system error'}

<b>Action Required:</b>
Please check the system logs and ensure all services are running.
        """

        return self.send_message(message.strip())

    def notify_system_start(self, port: int = 9000) -> bool:
        """
        Send system startup notification.

        Args:
            port: Web server port

        Returns:
            True if notification sent successfully
        """
        message = f"""
🚀 <b>GapSignal System Started</b>
━━━━━━━━━━━━━━━━━━━━
<b>Status:</b> System initialized and running
<b>Web Interface:</b> http://localhost:{port}
<b>API Status:</b> http://localhost:{port}/api/status

<b>Monitoring:</b>
• Data refresh every 5 minutes
• Signal detection active
• Telegram notifications enabled
        """

        return self.send_message(message.strip())

    def notify_system_stop(self) -> bool:
        """
        Send system shutdown notification.

        Returns:
            True if notification sent successfully
        """
        message = """
🛑 <b>GapSignal System Stopped</b>
━━━━━━━━━━━━━━━━━━━━
<b>Status:</b> System has been shut down

<b>Next Steps:</b>
• Check logs for shutdown reason
• Restart service when ready
        """

        return self.send_message(message.strip())

    def test_connection(self) -> bool:
        """
        Test Telegram bot connection.

        Returns:
            True if connection successful
        """
        if not self.enabled:
            return False

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get('ok'):
                username = data['result']['username']
                logger.info(f"Telegram bot connected: @{username}")
                return True
            else:
                error_desc = data.get('description', 'No description')
                logger.error(f"Telegram API error: {error_desc}")
                return False

        except requests.exceptions.HTTPError as e:
            # Try to get more details from response
            try:
                if e.response is not None:
                    error_details = e.response.json()
                    error_desc = error_details.get('description', 'No description')
                    logger.error(f"Telegram connection test failed ({e.response.status_code}): {error_desc}")
                    # Provide user-friendly guidance based on status code
                    if e.response.status_code == 401:
                        logger.error("Invalid bot token. Please check TELEGRAM_BOT_TOKEN in .env file.")
                    elif e.response.status_code == 403:
                        logger.error("Bot token is valid but missing permissions. Ensure bot is started with /start command.")
                    elif e.response.status_code == 404:
                        logger.error("Bot token not found. Please verify TELEGRAM_BOT_TOKEN.")
                else:
                    logger.error(f"Telegram HTTP error: {e}")
            except (ValueError, KeyError):
                logger.error(f"Telegram HTTP error: {e}")
            return False
        except Exception as e:
            logger.error(f"Telegram connection test failed: {e}")
            return False


# Global instance
telegram_notifier = TelegramNotifier()