# Luxi Trading AI Bot

A highly advanced Python stock trading bot that trades during market hours from 8:00 AM to 5:00 PM Eastern Time.

## What it does

- Fetches stock price data with `yfinance`
- Trains a lightweight logistic regression model to predict short-term direction
- Places and closes market trades with supported brokers
- Runs only during trading hours (8am–5pm ET)

## Security and access control

- This bot requires a secure owner name and password before startup.
- Set `TRADING_BOT_OWNER` and `TRADING_BOT_PASSWORD` before running.
- Do not commit secrets or password values to the repository.

## Requirements

- Python 3.10+
- `ccxt` for Binance support
- `requests` for generic REST broker support
- Alpaca paper trading account or other supported broker credentials
- Broker-specific environment variables

## Setup

1. Create a Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set broker environment variables.

### Binance

```bash
export TRADING_BROKER="BINANCE"
export BINANCE_API_KEY="your_key"
export BINANCE_API_SECRET="your_secret"
export BINANCE_TESTNET="true"
```

### Alpaca

```bash
export TRADING_BROKER="ALPACA"
export APCA_API_KEY_ID="your_key"
export APCA_API_SECRET_KEY="your_secret"
export APCA_API_BASE_URL="https://paper-api.alpaca.markets"
```

### FxPro / PocketBroker / Exness / Luno (generic REST API)

```bash
export TRADING_BROKER="FXPRO"
export FXPRO_API_BASE_URL="https://api.fxpro.example"
export FXPRO_API_KEY="your_key"
```

```bash
export TRADING_BROKER="POCKETBROKER"
export POCKETBROKER_API_BASE_URL="https://api.pocketbroker.example"
export POCKETBROKER_API_KEY="your_key"
```

```bash
export TRADING_BROKER="EXNESS"
export EXNESS_API_BASE_URL="https://api.exness.example"
export EXNESS_API_KEY="your_key"
```

```bash
export TRADING_BROKER="LUNO"
export LUNO_API_BASE_URL="https://api.luno.com"
export LUNO_API_KEY="your_key"
```

### MetaTrader 5

MetaTrader 5 support is available via the `MetaTrader5` package, but its installation may require a broker-compatible environment.

### Security variables

```bash
export TRADING_BOT_OWNER="lehlogonolo moloto"
export TRADING_BOT_PASSWORD="Lm070807"
```

4. Set symbols and run the bot:

```bash
export TRADING_SYMBOLS="AAPL,MSFT,GOOG"
python run.py
```

## Notes

- The bot trades only between 8:00 AM and 5:00 PM Eastern Time by default.
- It fetches historical price data with `yfinance`, trains a simple logistic regression model, and places market orders through the configured broker.
- `FXPRO` and `POCKETBROKER` use a generic REST interface and require a broker API that exposes position and order endpoints.
- Use paper trading or test environments until you confirm the strategy behavior.
