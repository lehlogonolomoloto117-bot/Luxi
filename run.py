import os
from src.trading_bot.bot import TradingBot


def verify_access() -> None:
    owner = os.getenv("TRADING_BOT_OWNER")
    password = os.getenv("TRADING_BOT_PASSWORD")
    expected_owner = "lehlogonolo moloto"
    expected_password = "Lm070807"

    if owner != expected_owner or password != expected_password:
        raise EnvironmentError(
            "Unauthorized: set TRADING_BOT_OWNER and TRADING_BOT_PASSWORD correctly before running."
        )


if __name__ == "__main__":
    verify_access()
    bot = TradingBot(
        symbols=None,
        trade_amount=5000,
        market_timezone="America/New_York",
        trade_start_hour=8,
        trade_end_hour=17,
        broker_name=None,
    )
    bot.run()
