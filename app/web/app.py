"""
Flask web application for GapSignal system.
"""
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

from flask import Flask, render_template, jsonify, request, send_from_directory
import plotly
import plotly.graph_objs as go
from plotly.subplots import make_subplots

from app.core.config import config
from app.api.data_fetcher import DataFetcher
from app.core.data_processor import DataProcessor
from app.api.binance_client import BinanceClient
from app.utils.telegram_notifier import telegram_notifier

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'gapsignal-secret-key-2024'

# Initialize components
binance_client = BinanceClient()
data_fetcher = DataFetcher(binance_client)
data_processor = DataProcessor(binance_client)

# Cache for processed data
_data_cache = {}
_cache_timestamp = 0
CACHE_DURATION = 300  # 5 minutes


def get_processed_data(force_refresh: bool = False) -> Dict[str, Any]:
    """Get processed data with caching."""
    global _data_cache, _cache_timestamp

    current_time = time.time()
    if not force_refresh and _data_cache and (current_time - _cache_timestamp) < CACHE_DURATION:
        logger.debug("Returning cached data")
        return _data_cache

    logger.info("Refreshing data cache...")

    try:
        # Get filtered symbols
        filtered_symbols, all_ticker_data = data_fetcher.get_filtered_symbols()

        # Extract symbol names - use all filtered symbols
        symbols = [s['symbol'] for s in filtered_symbols]

        # Process symbols
        processed_data = data_processor.process_multiple_symbols(
            symbols=symbols,
            ticker_data=all_ticker_data
        )

        # Filter signals
        buy_signals, sell_signals = data_processor.filter_by_signal(processed_data, min_confidence=0.6)

        # Generate summary
        summary = data_processor.generate_summary(processed_data)

        # Save previous cache for comparison
        previous_cache = _data_cache
        previous_buy_signals = previous_cache.get('buy_signals', []) if previous_cache else []
        previous_sell_signals = previous_cache.get('sell_signals', []) if previous_cache else []

        # Cache results
        _data_cache = {
            'processed_data': processed_data,
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'summary': summary,
            'timestamp': current_time,
            'symbol_count': len(processed_data),
            'buy_count': len(buy_signals),
            'sell_count': len(sell_signals)
        }
        _cache_timestamp = current_time

        logger.info(f"Data refresh complete: {len(processed_data)} symbols, "
                   f"{len(buy_signals)} buy signals, {len(sell_signals)} sell signals")

        # Send Telegram notifications for new signals
        if telegram_notifier.enabled:
            try:
                # Helper function to create signal signature for comparison
                def get_signal_signature(signal):
                    return f"{signal.get('symbol')}-{signal.get('confidence')}-{signal.get('current_price')}"

                # Find new buy signals (not in previous cache)
                previous_buy_set = {get_signal_signature(s) for s in previous_buy_signals}
                new_buy_signals = [s for s in buy_signals if get_signal_signature(s) not in previous_buy_set]

                # Find new sell signals (not in previous cache)
                previous_sell_set = {get_signal_signature(s) for s in previous_sell_signals}
                new_sell_signals = [s for s in sell_signals if get_signal_signature(s) not in previous_sell_set]

                # Send notifications for new buy signals
                for signal in new_buy_signals:
                    telegram_notifier.notify_signal(signal, 'buy')
                    time.sleep(0.5)  # Rate limiting

                # Send notifications for new sell signals
                for signal in new_sell_signals:
                    telegram_notifier.notify_signal(signal, 'sell')
                    time.sleep(0.5)  # Rate limiting

                # Send summary if we have new signals
                if new_buy_signals or new_sell_signals:
                    telegram_notifier.notify_summary(summary, len(processed_data))
                elif not previous_cache:  # First run, send summary even if no signals
                    telegram_notifier.notify_summary(summary, len(processed_data))

            except Exception as e:
                logger.warning(f"Failed to send Telegram notifications: {e}")

        return _data_cache

    except Exception as e:
        logger.error(f"Error processing data: {e}")
        # Return empty data structure on error
        return {
            'processed_data': [],
            'buy_signals': [],
            'sell_signals': [],
            'summary': {},
            'timestamp': current_time,
            'symbol_count': 0,
            'buy_count': 0,
            'sell_count': 0,
            'error': str(e)
        }


@app.route('/')
def index():
    """Main dashboard page."""
    data = get_processed_data()

    # Check if refresh was requested
    force_refresh = request.args.get('refresh', '').lower() == 'true'
    if force_refresh:
        data = get_processed_data(force_refresh=True)

    return render_template(
        'index.html',
        processed_data=data['processed_data'],
        buy_signals=data['buy_signals'],
        sell_signals=data['sell_signals'],
        summary=data['summary'],
        timestamp=datetime.fromtimestamp(data['timestamp']).strftime('%Y-%m-%d %H:%M:%S'),
        web_port=config.get('web_port', 6000)
    )


@app.route('/api/signals')
def api_signals():
    """API endpoint for signal data."""
    data = get_processed_data()

    # Filter by signal type if requested
    signal_type = request.args.get('type', '').lower()
    if signal_type == 'buy':
        signals = data['buy_signals']
    elif signal_type == 'sell':
        signals = data['sell_signals']
    else:
        signals = data['processed_data']

    return jsonify({
        'success': True,
        'data': signals,
        'summary': data['summary'],
        'timestamp': data['timestamp'],
        'count': len(signals)
    })


@app.route('/detail/<symbol>')
def detail(symbol: str):
    """Detail page for a specific symbol."""
    try:
        # Get symbol data
        symbol_data = data_fetcher.get_symbol_data(symbol)
        klines = symbol_data.get('klines', [])

        if not klines:
            return render_template('error.html', message=f"No data available for {symbol}")

        # Process symbol
        processed = data_processor.process_symbol(symbol, klines)

        # Generate chart
        chart_json = generate_symbol_chart(symbol, klines, processed)

        return render_template(
            'detail.html',
            symbol=symbol,
            data=processed,
            chart_json=chart_json,
            binance_url=f"https://www.binance.com/en/futures/{symbol}"
        )

    except Exception as e:
        logger.error(f"Error loading detail for {symbol}: {e}")
        return render_template('error.html', message=f"Error loading {symbol}: {str(e)}")


@app.route('/api/chart/<symbol>')
def api_chart(symbol: str):
    """API endpoint for chart data."""
    try:
        symbol_data = data_fetcher.get_symbol_data(symbol)
        klines = symbol_data.get('klines', [])

        if not klines:
            return jsonify({'success': False, 'error': 'No data available'})

        processed = data_processor.process_symbol(symbol, klines)
        chart_json = generate_symbol_chart(symbol, klines, processed)

        return jsonify({
            'success': True,
            'symbol': symbol,
            'chart': chart_json,
            'data': processed
        })

    except Exception as e:
        logger.error(f"Error generating chart for {symbol}: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/refresh')
def api_refresh():
    """API endpoint to refresh data cache."""
    data = get_processed_data(force_refresh=True)
    return jsonify({
        'success': True,
        'message': 'Data refreshed successfully',
        'summary': data['summary'],
        'timestamp': data['timestamp']
    })


@app.route('/api/status')
def api_status():
    """API endpoint for system status."""
    cache_stats = data_fetcher.get_cache_stats()
    connection_ok = data_fetcher.test_connection()

    return jsonify({
        'success': True,
        'status': 'online',
        'connection': 'ok' if connection_ok else 'failed',
        'cache': cache_stats,
        'config': {
            'web_port': config.get('web_port'),
            'volume_threshold': config.get('volume_threshold_usdt'),
            'price_change_threshold': config.get('price_change_threshold_percent'),
            'default_interval': config.get('default_kline_interval')
        },
        'timestamp': time.time()
    })


@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files."""
    return send_from_directory('static', filename)


def generate_symbol_chart(symbol: str, klines: List[List[Any]], processed_data: Dict[str, Any]) -> str:
    """Generate Plotly chart for a symbol."""
    if not klines:
        return json.dumps({'data': [], 'layout': {}})

    # Extract data
    dates = [datetime.fromtimestamp(k[0] / 1000) for k in klines]
    opens = [float(k[1]) for k in klines]
    highs = [float(k[2]) for k in klines]
    lows = [float(k[3]) for k in klines]
    closes = [float(k[4]) for k in klines]
    volumes = [float(k[5]) for k in klines]

    # Create subplots
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=(f'{symbol} Price Chart', 'Volume')
    )

    # Candlestick chart
    candlestick = go.Candlestick(
        x=dates,
        open=opens,
        high=highs,
        low=lows,
        close=closes,
        name='Price',
        showlegend=False
    )
    fig.add_trace(candlestick, row=1, col=1)

    # Add EMA lines if available
    ema_values = processed_data.get('ema_values', {})
    for period, value in sorted(ema_values.items()):
        if value and value > 0:
            # Calculate EMA values for all points
            from app.core.indicators import IndicatorCalculator
            calculator = IndicatorCalculator()
            ema_line = calculator.calculate_ema(closes, period)
            # Filter out NaN values
            valid_dates = [dates[i] for i, v in enumerate(ema_line) if not (isinstance(v, float) and (v != v or v == 0))]
            valid_ema = [v for v in ema_line if not (isinstance(v, float) and (v != v or v == 0))]
            if valid_ema:
                fig.add_trace(
                    go.Scatter(
                        x=valid_dates,
                        y=valid_ema,
                        name=f'EMA{period}',
                        line=dict(width=1),
                        opacity=0.7
                    ),
                    row=1, col=1
                )

    # Volume bars
    colors = ['green' if closes[i] >= opens[i] else 'red' for i in range(len(closes))]
    volume_bars = go.Bar(
        x=dates,
        y=volumes,
        name='Volume',
        marker_color=colors,
        showlegend=False
    )
    fig.add_trace(volume_bars, row=2, col=1)

    # Update layout
    fig.update_layout(
        title=f'{symbol} - {processed_data.get("signal", "No signal").upper()} Signal',
        yaxis_title='Price (USDT)',
        yaxis2_title='Volume',
        xaxis_rangeslider_visible=False,
        height=700,
        template='plotly_dark',
        hovermode='x unified'
    )

    # Update axes
    fig.update_xaxes(title_text='Time', row=2, col=1)
    fig.update_yaxes(title_text='Price (USDT)', row=1, col=1)
    fig.update_yaxes(title_text='Volume', row=2, col=1)

    # Add signal annotation if present
    signal = processed_data.get('signal')
    if signal in ['buy', 'sell']:
        last_date = dates[-1]
        last_price = closes[-1]

        fig.add_annotation(
            x=last_date,
            y=last_price,
            text=f'{signal.upper()} Signal',
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=2,
            arrowcolor='green' if signal == 'buy' else 'red',
            ax=0,
            ay=-40,
            bgcolor='green' if signal == 'buy' else 'red',
            font=dict(color='white', size=12)
        )

    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


if __name__ == '__main__':
    port = config.get('web_port', 6000)
    logger.info(f"Starting GapSignal web server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)