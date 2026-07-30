"""
Configuratie voor de Liquidity Grab bot.
"""

# Exchange
EXCHANGE = "kraken"

# Coins/pairs
USE_TOP_N_BY_VOLUME = True
TOP_N = 100
QUOTE_CURRENCY = "USD"
COINS = ["BTC/USD", "ETH/USD"]  # alleen gebruikt als USE_TOP_N_BY_VOLUME = False

# Timeframes (elk heeft zijn eigen losse workflow, net als bij de andere bot)
TIMEFRAMES = ["30m", "1h", "4h", "12h", "1d"]

CANDLE_LIMIT = 200  # aantal candles dat opgehaald wordt

# ================= SWING / LIQUIDITY-NIVEAU SETTINGS =================
# Een candle is een "swing high" als zijn high hoger is dan die van
# FRACTAL_N candles ervoor EN erna (en omgekeerd voor swing low).
FRACTAL_N = 5

# Een niveau moet minstens dit aantal candles oud zijn voordat een sweep
# ervan telt (voorkomt dat een net-gevormd, te vers niveau al meetelt).
MIN_LEVEL_AGE = 10

# Een niveau mag tussen het ontstaan en de sweep niet al eerder doorbroken
# (gesloten voorbij het niveau) zijn - anders is het niet meer "vers".
REQUIRE_UNTESTED_LEVEL = True

# Wiek moet minstens dit veelvoud van het candle-lichaam zijn om als
# een "hamer/sweep-candle" te tellen (voorkomt zwakke, kleine wieken).
MIN_WICK_TO_BODY_RATIO = 1.2

# Hoeveel candles terug worden doorzocht naar swing-niveaus
LEVEL_LOOKBACK = 150

# ================= CHART-AFBEELDING SETTINGS =================
SEND_CHART_IMAGE = True
CHART_LOOKBACK = 60   # aantal candles getoond in de afbeelding

# Bestand waarin de laatste bekende signaal-status wordt bijgehouden
STATE_FILE_TEMPLATE = "state-{timeframe}.json"
