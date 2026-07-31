"""
Hoofdscript: haalt candle-data op, checkt op liquidity grabs (sweep + hamer-candle
van een swing-niveau met voldoende leeftijd), en stuurt een Telegram-bericht +
chart-afbeelding zodra dat gebeurt.

Aanroepen:
  python scanner.py 1h    -> checkt alleen de opgegeven timeframe
  python scanner.py       -> checkt alle timeframes uit config.py
"""

import json
import os
import sys
import time
from datetime import datetime, timezone

import ccxt
import pandas as pd

import config as cfg
from liquidity import detect_liquidity_grab
from telegram import send_telegram_message, send_telegram_photo

TIMEFRAME_MINUTES = {
    "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "12h": 720, "1d": 1440,
}


def load_state(timeframe: str) -> dict:
    state_file = cfg.STATE_FILE_TEMPLATE.format(timeframe=timeframe)
    if os.path.exists(state_file):
        with open(state_file, "r") as f:
            return json.load(f)
    return {}


def save_state(state: dict, timeframe: str):
    state_file = cfg.STATE_FILE_TEMPLATE.format(timeframe=timeframe)
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)


def fetch_closed_ohlcv(exchange, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
    raw = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])

    tf_ms = TIMEFRAME_MINUTES[timeframe] * 60 * 1000
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    if len(df) > 0:
        last_close_time = df["timestamp"].iloc[-1] + tf_ms
        if last_close_time > now_ms:
            df = df.iloc[:-1]

    return df


def format_message(symbol: str, timeframe: str, result: dict, direction: str) -> str:
    level = result["level_price"]
    if direction == "SHORT":
        return (
            f"🎯 <b>LIQUIDITY GRAB SHORT: {symbol}</b> ({timeframe})\n"
            f"Sweep van niveau {level:.5f}, candle sloot weer terug eronder.\n"
            f"💰 Prijs: {result['close']}"
        )
    else:
        return (
            f"🎯 <b>LIQUIDITY GRAB LONG: {symbol}</b> ({timeframe})\n"
            f"Sweep van niveau {level:.5f}, candle sloot weer terug erboven.\n"
            f"💰 Prijs: {result['close']}"
        )


def get_top_n_symbols(exchange, quote: str, n: int) -> list:
    markets = exchange.load_markets()
    tickers = exchange.fetch_tickers()
    candidates = []
    for symbol, market in markets.items():
        if market.get("quote") != quote or not market.get("active", True):
            continue
        ticker = tickers.get(symbol)
        if not ticker or ticker.get("quoteVolume") is None:
            continue
        candidates.append((symbol, ticker["quoteVolume"]))
    candidates.sort(key=lambda x: x[1], reverse=True)
    return [symbol for symbol, _ in candidates[:n]]


def send_signal(symbol: str, timeframe: str, result: dict, direction: str, df: pd.DataFrame):
    message = format_message(symbol, timeframe, result, direction)

    if not cfg.SEND_CHART_IMAGE:
        send_telegram_message(message)
        return

    try:
        from chart import generate_chart
        image_path = f"/tmp/liqchart_{symbol.replace('/', '_')}_{timeframe}_{direction}.png"
        generate_chart(df, result, symbol, timeframe, direction, image_path, lookback=cfg.CHART_LOOKBACK)
        send_telegram_photo(image_path, caption=message)
        os.remove(image_path)
    except Exception as e:
        print(f"Chart-generatie mislukt voor {symbol}:{timeframe} ({e}), val terug op tekstbericht.")
        send_telegram_message(message)


def main():
    if len(sys.argv) > 1:
        timeframes_to_check = [sys.argv[1]]
        print(f"Alleen timeframe {sys.argv[1]} wordt gecheckt.")
    else:
        timeframes_to_check = cfg.TIMEFRAMES
        print(f"Alle timeframes worden gecheckt: {timeframes_to_check}")

    exchange_class = getattr(ccxt, cfg.EXCHANGE)
    exchange = exchange_class({"enableRateLimit": True})

    send_telegram_message("✅ Testbericht: de liquidity-grab-scanner draait en Telegram werkt!")

    if cfg.USE_TOP_N_BY_VOLUME:
        coins = get_top_n_symbols(exchange, cfg.QUOTE_CURRENCY, cfg.TOP_N)
        print(f"Top {cfg.TOP_N} op volume opgehaald: {len(coins)} pairs.")
    else:
        coins = cfg.COINS

    new_alerts = []

    for timeframe in timeframes_to_check:
        state = load_state(timeframe)

        for symbol in coins:
            key_short = f"{symbol}:{timeframe}:short"
            key_long = f"{symbol}:{timeframe}:long"
            try:
                df = fetch_closed_ohlcv(exchange, symbol, timeframe, cfg.CANDLE_LIMIT)
                if len(df) < cfg.LEVEL_LOOKBACK // 2:
                    print(f"Te weinig candles voor {symbol}:{timeframe}, sla over.")
                    continue

                result = detect_liquidity_grab(df, cfg)

                last_ts = int(df["timestamp"].iloc[-1])

                if result["short_signal"] and state.get(key_short) != last_ts:
                    send_signal(symbol, timeframe, result, "SHORT", df)
                    state[key_short] = last_ts
                    new_alerts.append(key_short)
                    print(f"SIGNAAL: {key_short}")

                if result["long_signal"] and state.get(key_long) != last_ts:
                    send_signal(symbol, timeframe, result, "LONG", df)
                    state[key_long] = last_ts
                    new_alerts.append(key_long)
                    print(f"SIGNAAL: {key_long}")

            except Exception as e:
                print(f"Fout bij {symbol}:{timeframe}: {e}")

            time.sleep(exchange.rateLimit / 1000)

        save_state(state, timeframe)

    print(f"Klaar. {len(new_alerts)} nieuwe signalen: {new_alerts}")


if __name__ == "__main__":
    main()
