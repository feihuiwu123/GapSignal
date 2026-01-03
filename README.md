# GapSignal Trading System

## Overview
GapSignal is an automated trading signal system for Binance futures that identifies buy/sell opportunities based on price gap patterns and technical indicators. The system filters trading pairs by volume and price change, detects signals using consecutive candle patterns, and provides a web interface for visualization.

## Features
1. **Trading Pair Filtering**: Filters Binance futures pairs with 24h volume > 50M USDT and price change > 1%
2. **Signal Detection**: Detects buy/sell signals based on N consecutive candles with cumulative change > 1% and increasing/decreasing low/close/high sequences
3. **Technical Analysis**: Calculates EMA20, EMA60, EMA120, EMA250 differences and other indicators (RSI, ATR, Bollinger Bands, MACD)
4. **Web Interface**: Real-time dashboard with signal tables, detailed charts, and Binance integration
5. **Configurable**: All parameters configurable via `config.json` and `.env` file

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     GapSignal System                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Web UI    │  │  Data       │  │   Signal    │        │
│  │   (Flask)   │◄─┤  Processor  │◄─┤   Detector  │        │
│  │             │  │             │  │             │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                │               │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐        │
│  │   Charts    │  │   Filter    │  │  Indicators │        │
│  │  (Plotly)   │  │  (Volume/   │  │   (EMA/     │        │
│  │             │  │   Change)    │  │   RSI/ATR)  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│         ▲                ▲                ▲               │
│         └────────────────┼────────────────┘               │
│                          │                                │
│                   ┌──────▼──────┐                         │
│                   │   Data      │                         │
│                   │   Fetcher   │                         │
│                   │  (Cached)   │                         │
│                   └──────┬──────┘                         │
│                          │                                │
│                   ┌──────▼──────┐                         │
│                   │  Binance    │                         │
│                   │    API      │                         │
│                   └─────────────┘                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
gapsignal/
├── app/                          # Application code
│   ├── api/                      # API clients
│   │   ├── binance_client.py     # Binance API wrapper
│   │   └── data_fetcher.py       # Data fetching with caching
│   ├── core/                     # Core logic
│   │   ├── config.py             # Configuration management
│   │   ├── signal_detector.py    # Signal detection algorithm
│   │   ├── data_processor.py     # Data processing pipeline
│   │   └── indicators.py         # Technical indicator calculations
│   ├── web/                      # Web interface
│   │   ├── app.py                # Flask application
│   │   ├── templates/            # HTML templates
│   │   └── static/               # Static assets
│   └── utils/                    # Utilities
│       ├── logger.py             # Logging configuration
│       └── helpers.py            # Helper functions
├── config/                       # Configuration directory
├── scripts/                      # Deployment scripts
├── tests/                        # Test files
├── .env                          # Environment variables
├── .env.example                  # Environment template
├── config.json                   # Application configuration
├── requirements.txt              # Python dependencies
└── main.py                       # Main entry point
```

## Installation

### Prerequisites
- Python 3.8+
- Binance API key and secret
- Ubuntu 20.04/22.04 (for production deployment)

### Local Development Setup

1. **Clone or copy the project**
   ```bash
   git clone <repository-url>
   cd gapsignal
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your Binance API keys
   ```

4. **Configure application settings**
   - Edit `config.json` for threshold adjustments
   - Default configuration:
     ```json
     {
       "volume_threshold_usdt": 50000000,
       "price_change_threshold_percent": 1.0,
       "default_kline_interval": "15m",
       "available_intervals": ["1m", "5m", "15m", "1h", "4h", "1d"],
       "signal_lookback_periods": 3,
       "signal_cumulative_change_threshold_percent": 1.0,
       "web_port": 6000,
       "ema_periods": [20, 60, 120, 250]
     }
     ```

5. **Run the application**
   ```bash
   python main.py
   ```

6. **Access the web interface**
   - Open browser to `http://localhost:6000`

### Production Deployment (Ubuntu)

Use the provided deployment scripts:

1. **Full installation**
   ```bash
   sudo ./scripts/setup_ubuntu.sh
   ```

2. **Or use the deploy script**
   ```bash
   sudo ./scripts/deploy.sh install
   ```

3. **Manage the service**
   ```bash
   sudo ./scripts/deploy.sh start      # Start service
   sudo ./scripts/deploy.sh stop       # Stop service
   sudo ./scripts/deploy.sh restart    # Restart service
   sudo ./scripts/deploy.sh status     # Check status
   sudo ./scripts/deploy.sh update     # Update application
   ```

## Configuration

### Environment Variables (`.env`)
```bash
# Binance API Configuration
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here

# Telegram Configuration (optional)
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### Application Configuration (`config.json`)
```json
{
  "volume_threshold_usdt": 50000000,
  "price_change_threshold_percent": 1.0,
  "default_kline_interval": "15m",
  "available_intervals": ["1m", "5m", "15m", "1h", "4h", "1d"],
  "signal_lookback_periods": 3,
  "signal_cumulative_change_threshold_percent": 1.0,
  "web_port": 6000,
  "ema_periods": [20, 60, 120, 250]
}
```

## Signal Detection Algorithm

### Buy Signal Conditions
1. **Cumulative Change**: Last N candles cumulative change > threshold (default: 1%)
2. **Price Sequences**: All three price series must be strictly increasing:
   - `low[-N] < low[-N+1] < ... < low[-1]`
   - `close[-N] < close[-N+1] < ... < close[-1]`
   - `high[-N] < high[-N+1] < ... < high[-1]`

### Sell Signal Conditions
1. **Cumulative Change**: Last N candles cumulative change < -threshold (default: -1%)
2. **Price Sequences**: All three price series must be strictly decreasing:
   - `low[-N] > low[-N+1] > ... > low[-1]`
   - `close[-N] > close[-N+1] > ... > close[-1]`
   - `high[-N] > high[-N+1] > ... > high[-1]`

### Confidence Calculation
- Confidence increases from 50% to 100% as the cumulative change exceeds the threshold
- Formula: `confidence = 0.5 + (excess / threshold) * 0.5`

## Web Interface Features

### Dashboard
- Real-time signal tables with sorting and filtering
- Buy/sell signal indicators with confidence scores
- 24h volume and price change statistics
- EMA difference columns (EMA20, EMA60, EMA120, EMA250)
- Direct links to Binance trading pages

### Detail View
- Interactive candlestick charts with EMA overlays
- Technical indicator panels (RSI, ATR, Bollinger Bands, MACD)
- Signal analysis and trading considerations
- Volume histogram

### API Endpoints
- `GET /api/signals` - Get all signal data
- `GET /api/chart/<symbol>` - Get chart data for specific symbol
- `GET /api/refresh` - Force data refresh
- `GET /api/status` - System status and health check

## Deployment Architecture

### System Components
1. **GapSignal Application** - Python Flask app (port 6000)
2. **Nginx** - Reverse proxy and static file server
3. **Systemd** - Service management and auto-restart
4. **UFW Firewall** - Security hardening

### Service Management
```bash
# Systemd service commands
systemctl status gapsignal
systemctl start gapsignal
systemctl stop gapsignal
systemctl restart gapsignal
journalctl -u gapsignal -f  # View logs
```

### Nginx Configuration
- Reverse proxy from port 80 to 6000
- Static file serving
- Security headers
- WebSocket support

## Monitoring and Maintenance

### Log Files
- Application logs: `/var/log/gapsignal/gapsignal.log`
- System logs: `journalctl -u gapsignal`
- Nginx logs: `/var/log/nginx/access.log`, `/var/log/nginx/error.log`

### Performance Monitoring
- Data cache statistics via `/api/status`
- API rate limiting awareness
- Memory usage monitoring

### Backup Recommendations
1. Configuration files:
   - `/opt/gapsignal/.env`
   - `/opt/gapsignal/config.json`
   - `/etc/gapsignal/config.json`
2. Log rotation configured (10MB max, 5 backups)

## Troubleshooting

### Common Issues

1. **Binance API Connection Failed**
   - Check API keys in `.env` file
   - Verify network connectivity to Binance
   - Ensure API key has futures trading permissions

2. **No Signals Detected**
   - Adjust thresholds in `config.json`
   - Check market conditions (volatility, volume)
   - Verify data fetching is working

3. **Web Interface Not Accessible**
   - Check if service is running: `systemctl status gapsignal`
   - Verify port 6000 is accessible
   - Check firewall settings

4. **High Memory Usage**
   - Reduce number of symbols processed
   - Increase cache duration
   - Monitor with `htop` or `journalctl`

### Debug Mode
Run with debug logging:
```bash
python main.py  # Check logs in gapsignal.log
```

## Security Considerations

1. **API Keys**: Never commit `.env` file to version control
2. **Firewall**: Only expose necessary ports (80, 443, 22)
3. **Service Account**: Run as non-root user (`www-data`)
4. **Updates**: Regularly update dependencies and system packages
5. **Monitoring**: Set up alerting for service failures

## Development

### Adding New Indicators
1. Add calculation method in `app/core/indicators.py`
2. Integrate into data processing pipeline in `app/core/data_processor.py`
3. Update web interface to display new indicator

### Modifying Signal Logic
1. Edit `app/core/signal_detector.py`
2. Update configuration parameters in `config.json`
3. Test with historical data

### Testing
Run unit tests:
```bash
python -m pytest tests/
```

## License
[Specify your license here]

## Support
For issues and feature requests, please check the GitHub repository or contact the development team.

---
*This system is for educational and research purposes only. Trading cryptocurrencies involves significant risk. Past performance is not indicative of future results.*