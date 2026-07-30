"""
Detectielogica voor liquidity grabs:
1. Vind swing-highs/lows (niveaus met "tijdsopbouw") via een fractal-methode.
2. Check of de laatste (gesloten) candle zo'n niveau met een wiek "sweept"
   en weer terugsluit - dat is de liquidity grab / hamer-candle.
"""

import numpy as np
import pandas as pd


def find_swing_points(df: pd.DataFrame, fractal_n: int) -> tuple:
    """
    Retourneert (swing_high_indices, swing_low_indices): lijsten met index-
    posities in df die een bevestigd swing-high/low zijn (fractal-methode).
    Een swing-punt kan pas bevestigd worden als er nog fractal_n candles ná
    liggen - de laatste fractal_n candles van de dataset zijn dus nooit
    (nog) een bevestigd swing-punt.
    """
    highs = df["high"].values
    lows = df["low"].values
    n = len(df)

    swing_high_idx = []
    swing_low_idx = []

    for i in range(fractal_n, n - fractal_n):
        window_high = highs[i - fractal_n: i + fractal_n + 1]
        if highs[i] == window_high.max() and np.sum(window_high == highs[i]) == 1:
            swing_high_idx.append(i)

        window_low = lows[i - fractal_n: i + fractal_n + 1]
        if lows[i] == window_low.min() and np.sum(window_low == lows[i]) == 1:
            swing_low_idx.append(i)

    return swing_high_idx, swing_low_idx


def _is_level_untested(df: pd.DataFrame, level_idx: int, level_price: float, last_idx: int, above: bool) -> bool:
    """Check of het niveau, sinds het ontstond, niet al eerder is doorbroken (close voorbij het niveau)."""
    closes = df["close"].values
    segment = closes[level_idx + 1: last_idx]
    if len(segment) == 0:
        return True
    if above:
        return not np.any(segment > level_price)
    else:
        return not np.any(segment < level_price)


def detect_liquidity_grab(df: pd.DataFrame, cfg) -> dict:
    """
    Checkt de laatste (gesloten) candle in df op een liquidity grab:
    - SHORT: candle sweept een swing-high (wiek erboven) en sluit weer onder het niveau.
    - LONG: candle sweept een swing-low (wiek eronder) en sluit weer boven het niveau.

    Retourneert een dict met o.a. 'short_signal' / 'long_signal' (bool) en het
    geraakte niveau + de index ervan (voor de chart-markering).
    """
    n = len(df)
    last_idx = n - 1
    last = df.iloc[-1]

    lookback_start = max(0, n - cfg.LEVEL_LOOKBACK)
    sub_df = df.iloc[lookback_start:n].reset_index(drop=True)
    offset = lookback_start

    swing_high_idx, swing_low_idx = find_swing_points(sub_df, cfg.FRACTAL_N)

    body = abs(last["close"] - last["open"])
    if body == 0:
        body = 1e-9
    upper_wick = last["high"] - max(last["open"], last["close"])
    lower_wick = min(last["open"], last["close"]) - last["low"]

    result = {
        "short_signal": False,
        "long_signal": False,
        "level_price": None,
        "level_index": None,
    }

    # ===== SHORT: sweep van een swing-high =====
    candidate_highs = [
        (offset + i, sub_df["high"].iloc[i]) for i in swing_high_idx
        if (last_idx - (offset + i)) >= cfg.MIN_LEVEL_AGE and (offset + i) < last_idx
    ]
    candidate_highs.sort(key=lambda x: x[1])
    for level_idx, level_price in candidate_highs:
        if last["high"] <= level_price:
            continue
        if last["close"] >= level_price:
            continue
        if upper_wick < cfg.MIN_WICK_TO_BODY_RATIO * body:
            continue
        if cfg.REQUIRE_UNTESTED_LEVEL and not _is_level_untested(df, level_idx, level_price, last_idx, above=True):
            continue
        result["short_signal"] = True
        result["level_price"] = float(level_price)
        result["level_index"] = level_idx
        break

    # ===== LONG: sweep van een swing-low =====
    if not result["short_signal"]:
        candidate_lows = [
            (offset + i, sub_df["low"].iloc[i]) for i in swing_low_idx
            if (last_idx - (offset + i)) >= cfg.MIN_LEVEL_AGE and (offset + i) < last_idx
        ]
        candidate_lows.sort(key=lambda x: x[1], reverse=True)
        for level_idx, level_price in candidate_lows:
            if last["low"] >= level_price:
                continue
            if last["close"] <= level_price:
                continue
            if lower_wick < cfg.MIN_WICK_TO_BODY_RATIO * body:
                continue
            if cfg.REQUIRE_UNTESTED_LEVEL and not _is_level_untested(df, level_idx, level_price, last_idx, above=False):
                continue
            result["long_signal"] = True
            result["level_price"] = float(level_price)
            result["level_index"] = level_idx
            break

    result["close"] = float(last["close"])
    return result
