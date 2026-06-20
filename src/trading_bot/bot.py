import os
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.linear_model import LogisticRegression

from .brokers import BrokerFactory, BrokerInterface


class TradingBot:
    def __init__(
        self,
        symbols: list[str] | None = None,
        trade_amount: float = 5000,
        market_timezone: str = "America/New_York",
        trade_start_hour: int = 8,
        trade_end_hour: int = 17,
        broker_name: str | None = None,
    ):
        self.symbols = symbols or self._load_symbols_from_env()
        self.trade_amount = trade_amount
        self.market_tz = ZoneInfo(market_timezone)
        self.trade_start_hour = trade_start_hour
        self.trade_end_hour = trade_end_hour
        self.broker = self._create_broker(broker_name)
        self.model = LogisticRegression(solver="liblinear")

    def _load_symbols_from_env(self) -> list[str]:
        symbols_raw = os.getenv("TRADING_SYMBOLS", "AAPL,MSFT,GOOG")
        return [symbol.strip().upper() for symbol in symbols_raw.split(",") if symbol.strip()]

    def _load_broker_from_env(self) -> str:
        return os.getenv("TRADING_BROKER", "BINANCE")

    def _create_broker(self, broker_name: str | None) -> BrokerInterface:
        name = broker_name or self._load_broker_from_env()
        print(f"[INIT] Using broker: {name}")
        return BrokerFactory.create(name)

    def _now(self) -> datetime:
        return datetime.now(tz=self.market_tz)

    def _in_trading_window(self, now: datetime) -> bool:
        start = now.replace(hour=self.trade_start_hour, minute=0, second=0, microsecond=0)
        end = now.replace(hour=self.trade_end_hour, minute=0, second=0, microsecond=0)
        return start <= now <= end

    def _next_start(self, now: datetime) -> datetime:
        start = now.replace(hour=self.trade_start_hour, minute=0, second=0, microsecond=0)
        if now < start:
            return start
        return start + timedelta(days=1)

    def _sleep_until(self, target: datetime) -> None:
        seconds = max((target - self._now()).total_seconds(), 0)
        if seconds > 0:
            time.sleep(seconds)

    def _fetch_historical_data(self, symbol: str) -> pd.DataFrame:
        history = yf.download(symbol, period="90d", interval="60m", progress=False, threads=False)
        if history.empty:
            raise RuntimeError(f"Unable to fetch data for {symbol}")

        history = history.dropna()
        history["return"] = history["Close"].pct_change()
        history["ma_5"] = history["Close"].rolling(5).mean()
        history["ma_10"] = history["Close"].rolling(10).mean()
        history["volatility"] = history["return"].rolling(10).std()
        history = history.dropna()
        return history

    def _prepare_training_data(self, history: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        history = history.copy()
        history["target"] = (history["Close"].shift(-1) > history["Close"]).astype(int)
        history = history.dropna()

        features = history[["return", "ma_5", "ma_10", "volatility"]]
        features = features.fillna(method="ffill").fillna(0)
        targets = history["target"].to_numpy()
        return features.to_numpy(), targets

    def _train_model(self, X: np.ndarray, y: np.ndarray) -> None:
        if len(y) < 20:
            raise ValueError("Not enough data to train the model")
        self.model.fit(X, y)

    def _build_prediction_features(self, history: pd.DataFrame) -> np.ndarray:
        last = history.iloc[-1]
        return np.array([
            last["return"],
            last["ma_5"],
            last["ma_10"],
            last["volatility"],
        ]).reshape(1, -1)

    def _should_trade(self, symbol: str) -> bool:
        try:
            history = self._fetch_historical_data(symbol)
            X, y = self._prepare_training_data(history)
            self._train_model(X, y)
            features = self._build_prediction_features(history)
            prediction = self.model.predict(features)[0]
            return bool(prediction)
        except Exception as exc:
            print(f"[ERROR] Skipping {symbol}: {exc}")
            return False

    def _get_position(self, symbol: str) -> float:
        try:
            return self.broker.get_position(symbol)
        except Exception as exc:
            print(f"[ERROR] Failed to get position for {symbol}: {exc}")
            return 0.0

    def _buy(self, symbol: str) -> None:
        print(f"[ACTION] Buying {symbol} using {self.broker.name()}")
        self.broker.buy(symbol, self.trade_amount)

    def _sell(self, symbol: str) -> None:
        print(f"[ACTION] Selling {symbol} using {self.broker.name()}")
        self.broker.sell(symbol, self.trade_amount)

    def _close_position(self, symbol: str) -> None:
        print(f"[ACTION] Closing position for {symbol} on {self.broker.name()}")
        self.broker.close_position(symbol)

    def _trade_symbol(self, symbol: str) -> None:
        signal = self._should_trade(symbol)
        position_qty = self._get_position(symbol)

        if signal:
            if position_qty > 0:
                print(f"[INFO] Already long {symbol} with qty {position_qty}")
                return
            self._buy(symbol)
        else:
            if position_qty > 0:
                self._close_position(symbol)
            else:
                print(f"[INFO] No trade signal for {symbol}")

    def run(self) -> None:
        print(f"Starting trading bot for symbols: {', '.join(self.symbols)}")
        while True:
            now = self._now()
            if self._in_trading_window(now):
                print(f"[RUN] Trading window active at {now.isoformat()}")
                for symbol in self.symbols:
                    self._trade_symbol(symbol)
                time.sleep(60)
            else:
                next_start = self._next_start(now)
                print(f"[WAIT] Market closed. Sleeping until {next_start.isoformat()}")
                self._sleep_until(next_start)
