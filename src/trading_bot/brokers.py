import os
from abc import ABC, abstractmethod
from typing import Any

import requests

try:
    import ccxt
except ImportError:  # pragma: no cover
    ccxt = None

try:
    import MetaTrader5 as mt5
except ImportError:  # pragma: no cover
    mt5 = None

try:
    import alpaca_trade_api as tradeapi
except ImportError:  # pragma: no cover
    tradeapi = None


class BrokerInterface(ABC):
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_position(self, symbol: str) -> float:
        raise NotImplementedError

    @abstractmethod
    def get_price(self, symbol: str) -> float:
        raise NotImplementedError

    @abstractmethod
    def buy(self, symbol: str, amount_usd: float) -> Any:
        raise NotImplementedError

    @abstractmethod
    def sell(self, symbol: str, amount_usd: float) -> Any:
        raise NotImplementedError

    @abstractmethod
    def close_position(self, symbol: str) -> Any:
        raise NotImplementedError


class BinanceBroker(BrokerInterface):
    def __init__(self):
        if ccxt is None:
            raise ImportError("ccxt is required for Binance support. Install with `pip install ccxt`.")

        key = os.getenv("BINANCE_API_KEY")
        secret = os.getenv("BINANCE_API_SECRET")
        sandbox = os.getenv("BINANCE_TESTNET", "false").lower() in ("1", "true", "yes")

        if not key or not secret:
            raise EnvironmentError("Missing Binance credentials. Set BINANCE_API_KEY and BINANCE_API_SECRET.")

        self.client = ccxt.binance({
            "apiKey": key,
            "secret": secret,
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},
        })

        if sandbox:
            self.client.set_sandbox_mode(True)

    def name(self) -> str:
        return "BINANCE"

    def _pair(self, symbol: str) -> str:
        if "/" in symbol:
            return symbol
        return f"{symbol}/USDT"

    def get_position(self, symbol: str) -> float:
        pair = self._pair(symbol)
        balance = self.client.fetch_balance()
        base = pair.split("/")[0]
        return float(balance.get(base, {}).get("free", 0.0))

    def get_price(self, symbol: str) -> float:
        pair = self._pair(symbol)
        ticker = self.client.fetch_ticker(pair)
        return float(ticker["last"])

    def buy(self, symbol: str, amount_usd: float) -> Any:
        pair = self._pair(symbol)
        price = self.get_price(symbol)
        quantity = amount_usd / price
        quantity = float(self.client.amount_to_precision(pair, quantity))
        if quantity <= 0:
            raise ValueError("Calculated zero quantity for buy order")
        print(f"[BROKER] Binance market buy {quantity} {pair}")
        return self.client.create_market_buy_order(pair, quantity)

    def sell(self, symbol: str, amount_usd: float) -> Any:
        pair = self._pair(symbol)
        price = self.get_price(symbol)
        quantity = amount_usd / price
        quantity = float(self.client.amount_to_precision(pair, quantity))
        if quantity <= 0:
            raise ValueError("Calculated zero quantity for sell order")
        print(f"[BROKER] Binance market sell {quantity} {pair}")
        return self.client.create_market_sell_order(pair, quantity)

    def close_position(self, symbol: str) -> Any:
        pair = self._pair(symbol)
        base = pair.split("/")[0]
        balance = self.client.fetch_balance()
        qty = float(balance.get(base, {}).get("free", 0.0))
        if qty <= 0:
            return None
        qty = float(self.client.amount_to_precision(pair, qty))
        print(f"[BROKER] Binance close {qty} {pair}")
        return self.client.create_market_sell_order(pair, qty)


class AlpacaBroker(BrokerInterface):
    def __init__(self):
        if tradeapi is None:
            raise ImportError("alpaca-trade-api is required for Alpaca support.")

        key = os.getenv("APCA_API_KEY_ID")
        secret = os.getenv("APCA_API_SECRET_KEY")
        base_url = os.getenv("APCA_API_BASE_URL", "https://paper-api.alpaca.markets")

        if not key or not secret:
            raise EnvironmentError("Missing Alpaca credentials. Set APCA_API_KEY_ID and APCA_API_SECRET_KEY.")

        self.client = tradeapi.REST(key, secret, base_url=base_url, api_version="v2")

    def name(self) -> str:
        return "ALPACA"

    def get_position(self, symbol: str) -> float:
        try:
            position = self.client.get_position(symbol)
            return float(position.qty)
        except Exception:
            return 0.0

    def get_price(self, symbol: str) -> float:
        ticker = __import__("yfinance").Ticker(symbol)
        quote = ticker.history(period="1d", interval="1m")
        if quote.empty:
            raise RuntimeError(f"Unable to fetch price for {symbol}")
        return float(quote["Close"].iloc[-1])

    def buy(self, symbol: str, amount_usd: float) -> Any:
        price = self.get_price(symbol)
        qty = int(max(amount_usd / price, 1))
        if qty <= 0:
            raise ValueError("Calculated zero quantity for buy order")
        print(f"[BROKER] Alpaca market buy {qty} {symbol}")
        return self.client.submit_order(symbol=symbol, qty=qty, side="buy", type="market", time_in_force="day")

    def sell(self, symbol: str, amount_usd: float) -> Any:
        position_qty = self.get_position(symbol)
        if position_qty <= 0:
            return None
        print(f"[BROKER] Alpaca market sell {position_qty} {symbol}")
        return self.client.submit_order(symbol=symbol, qty=int(position_qty), side="sell", type="market", time_in_force="day")

    def close_position(self, symbol: str) -> Any:
        return self.sell(symbol, 0.0)


class MetaTrader5Broker(BrokerInterface):
    def __init__(self):
        if mt5 is None:
            raise ImportError("MetaTrader5 package is required for MT5 support.")
        if not mt5.initialize():
            raise RuntimeError("Unable to initialize MetaTrader 5")

    def name(self) -> str:
        return "MT5"

    def get_position(self, symbol: str) -> float:
        positions = mt5.positions_get(symbol=symbol)
        if positions is None or len(positions) == 0:
            return 0.0
        return float(sum(pos.volume for pos in positions))

    def get_price(self, symbol: str) -> float:
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise RuntimeError(f"Unable to read symbol tick for {symbol}")
        return float(tick.ask)

    def buy(self, symbol: str, amount_usd: float) -> Any:
        price = self.get_price(symbol)
        volume = max(0.01, round(amount_usd / price / 100000, 2))
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": mt5.ORDER_TYPE_BUY,
            "price": price,
            "deviation": 20,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        print(f"[BROKER] MT5 order buy {volume} {symbol}")
        return mt5.order_send(request)

    def sell(self, symbol: str, amount_usd: float) -> Any:
        position_qty = self.get_position(symbol)
        if position_qty <= 0:
            return None
        price = mt5.symbol_info_tick(symbol).bid
        volume = position_qty
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": mt5.ORDER_TYPE_SELL,
            "price": price,
            "deviation": 20,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }
        print(f"[BROKER] MT5 order sell {volume} {symbol}")
        return mt5.order_send(request)

    def close_position(self, symbol: str) -> Any:
        return self.sell(symbol, 0.0)


class GenericRestBroker(BrokerInterface):
    def __init__(self, name: str, base_url_env: str, api_key_env: str):
        self._name = name
        self.base_url = os.getenv(base_url_env)
        self.api_key = os.getenv(api_key_env)
        if not self.base_url or not self.api_key:
            raise EnvironmentError(
                f"Missing credentials for {name}. Set {base_url_env} and {api_key_env}."
            )
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"})

    def name(self) -> str:
        return self._name

    def get_position(self, symbol: str) -> float:
        response = self.session.get(f"{self.base_url}/positions/{symbol}")
        response.raise_for_status()
        data = response.json()
        return float(data.get("quantity", 0.0))

    def get_price(self, symbol: str) -> float:
        response = self.session.get(f"{self.base_url}/market/{symbol}/quote")
        response.raise_for_status()
        data = response.json()
        return float(data["price"])

    def buy(self, symbol: str, amount_usd: float) -> Any:
        payload = {"symbol": symbol, "side": "buy", "amount_usd": amount_usd}
        response = self.session.post(f"{self.base_url}/orders", json=payload)
        response.raise_for_status()
        return response.json()

    def sell(self, symbol: str, amount_usd: float) -> Any:
        position = self.get_position(symbol)
        if position <= 0:
            return None
        payload = {"symbol": symbol, "side": "sell", "quantity": position}
        response = self.session.post(f"{self.base_url}/orders", json=payload)
        response.raise_for_status()
        return response.json()

    def close_position(self, symbol: str) -> Any:
        position = self.get_position(symbol)
        if position <= 0:
            return None
        payload = {"symbol": symbol, "side": "sell", "quantity": position}
        response = self.session.post(f"{self.base_url}/orders", json=payload)
        response.raise_for_status()
        return response.json()


class BrokerFactory:
    @staticmethod
    def create(name: str) -> BrokerInterface:
        normalized = name.strip().upper()
        if normalized == "BINANCE":
            return BinanceBroker()
        if normalized == "ALPACA":
            return AlpacaBroker()
        if normalized in {"MT5", "METATRADER5", "META TRADER 5", "META_TRADE_5"}:
            return MetaTrader5Broker()
        if normalized == "FXPRO":
            return GenericRestBroker("FXPRO", "FXPRO_API_BASE_URL", "FXPRO_API_KEY")
        if normalized == "POCKETBROKER":
            return GenericRestBroker("POCKETBROKER", "POCKETBROKER_API_BASE_URL", "POCKETBROKER_API_KEY")
        if normalized == "EXNESS":
            return GenericRestBroker("EXNESS", "EXNESS_API_BASE_URL", "EXNESS_API_KEY")
        if normalized == "LUNO":
            return GenericRestBroker("LUNO", "LUNO_API_BASE_URL", "LUNO_API_KEY")
        raise ValueError(
            f"Unsupported broker '{name}'. Supported brokers: BINANCE, ALPACA, MT5, FXPRO, POCKETBROKER, EXNESS, LUNO."
        )
