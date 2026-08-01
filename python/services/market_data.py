import os
import threading

import yfinance as yf
from datetime import datetime, timedelta

from services.indicator_service import IndicatorService
from services.nse_data import NSEDataService, strip_yf_suffix

# List of symbols with F&O (futures & options) contracts. OI data
# only exists for these, so we skip the extra NSE call entirely for
# anything not on this list.
_FNO_LIST_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "fno_list.txt"
)


def _load_fno_set():

    try:
        with open(_FNO_LIST_PATH, "r") as f:
            return {
                strip_yf_suffix(line.strip()).upper()
                for line in f
                if line.strip()
            }
    except Exception as e:
        print(f"Could not load fno_list.txt: {e}")
        return set()


FNO_SYMBOLS = _load_fno_set()


class MarketDataService:
    """
    Hybrid data source:
      - OHLCV price history + indicators + index change -> yfinance
        (reliable, well-tested library; feeds everything downstream)
      - Delivery % / delivery change + F&O OI change     -> NSE
        (the only two fields yfinance doesn't have)

    If NSE is blocked, down, or changes shape, only
    delivery_percentage / delivery_change / oi_change come back as
    None -- price data and every indicator keep working normally,
    since they never touch NSE.
    """

    def __init__(self):
        self.nse = NSEDataService()

        # Cache the index's own daily % change so a full watchlist
        # scan only fetches it once, not once per symbol.
        self._index_change_cache = None
        self._index_change_cache_date = None
        self._index_lock = threading.Lock()

    # --------------------------------------------------
    # INDEX CHANGE (RELATIVE STRENGTH BENCHMARK) - yfinance
    # --------------------------------------------------

    def get_index_change(self):

        today = datetime.today().date()

        with self._index_lock:

            if (
                self._index_change_cache is not None
                and self._index_change_cache_date == today
            ):
                return self._index_change_cache

            try:

                index_ticker = yf.Ticker("^NSEI")

                end = datetime.today()
                start = end - timedelta(days=10)

                index_df = index_ticker.history(
                    start=start, end=end, auto_adjust=False
                )

                if index_df.empty or len(index_df) < 2:
                    return None

                index_change = IndicatorService.price_change(
                    index_df
                ).iloc[-1]

                if index_change is None:
                    return None

                index_change = round(float(index_change), 2)

                self._index_change_cache = index_change
                self._index_change_cache_date = today

                return index_change

            except Exception as e:
                print(f"Index change fetch error: {e}")
                return None

    # --------------------------------------------------
    # PER-STOCK DATA
    # --------------------------------------------------

    def get_stock_data(self, symbol):

        try:

            ticker = yf.Ticker(symbol)

            end = datetime.today()
            start = end - timedelta(days=120)

            df = ticker.history(
                start=start, end=end, auto_adjust=False
            )

            if df.empty or len(df) < 50:
                return None

            # Fix MultiIndex columns if required
            if hasattr(df.columns, "levels"):
                df.columns = df.columns.get_level_values(0)

            # ====================================================
            # Calculate Indicators
            # ====================================================

            df["PriceChange"] = IndicatorService.price_change(df)

            df["VolumeChange"] = IndicatorService.volume_change(df)

            df["EMA20"] = IndicatorService.ema(df, 20)

            df["EMA50"] = IndicatorService.ema(df, 50)

            df["SMA20"] = IndicatorService.sma(df, 20)

            df["VWAP"] = IndicatorService.vwap(df)

            df["RSI"] = IndicatorService.rsi(df)

            df["ATR"] = IndicatorService.atr(df)

            df["VolumeSpike"] = IndicatorService.volume_spike(df)

            upper, middle, lower = IndicatorService.bollinger(df)

            df["BBUpper"] = upper
            df["BBMiddle"] = middle
            df["BBLower"] = lower

            macd, signal, hist = IndicatorService.macd(df)

            df["MACD"] = macd
            df["MACDSignal"] = signal
            df["MACDHistogram"] = hist

            # ====================================================
            # Current & Previous Candle
            # ====================================================

            prev = df.iloc[-2]

            curr = df.iloc[-1]

            # ====================================================
            # NSE extras: delivery % / delivery change, F&O OI
            # ====================================================

            delivery = self.nse.get_delivery_data(symbol)

            bare_symbol = strip_yf_suffix(symbol).upper()

            if bare_symbol in FNO_SYMBOLS:
                oi_change = self.nse.get_oi_change(symbol)
            else:
                oi_change = None

            # ====================================================
            # Return Dictionary
            # ====================================================

            return {

                # -----------------------
                # Basic
                # -----------------------

                "symbol": symbol,

                "prev_open": float(prev["Open"]),
                "prev_high": float(prev["High"]),
                "prev_low": float(prev["Low"]),
                "prev_close": float(prev["Close"]),
                "prev_volume": int(prev["Volume"]),

                "curr_open": float(curr["Open"]),
                "curr_high": float(curr["High"]),
                "curr_low": float(curr["Low"]),
                "curr_close": float(curr["Close"]),
                "curr_volume": int(curr["Volume"]),

                # -----------------------
                # Calculated
                # -----------------------

                "price_change": round(float(curr["PriceChange"]), 2),

                "volume_change": round(float(curr["VolumeChange"]), 2),

                "ema20": round(float(curr["EMA20"]), 2),

                "ema50": round(float(curr["EMA50"]), 2),

                "sma20": round(float(curr["SMA20"]), 2),

                "vwap": round(float(curr["VWAP"]), 2),

                "rsi": round(float(curr["RSI"]), 2),

                "atr": round(float(curr["ATR"]), 2),

                "volume_spike": round(float(curr["VolumeSpike"]), 2),

                "macd": round(float(curr["MACD"]), 2),

                "macd_signal": round(float(curr["MACDSignal"]), 2),

                "macd_histogram": round(float(curr["MACDHistogram"]), 2),

                "bb_upper": round(float(curr["BBUpper"]), 2),

                "bb_middle": round(float(curr["BBMiddle"]), 2),

                "bb_lower": round(float(curr["BBLower"]), 2),

                # -----------------------
                # Trend
                # -----------------------

                "trend": IndicatorService.trend(df),

                "breakout": bool(IndicatorService.breakout(df)),

                "breakdown": bool(IndicatorService.breakdown(df)),

                "volatility": round(
                    float(
                        IndicatorService.volatility(df).iloc[-1]
                    ),
                    2
                ),

                "gap": round(
                    float(
                        IndicatorService.gap(df).iloc[-1]
                    ),
                    2
                ),

                "candle_body": round(
                    IndicatorService.candle_body(df),
                    2
                ),

                "upper_wick": round(
                    IndicatorService.upper_wick(df),
                    2
                ),

                "lower_wick": round(
                    IndicatorService.lower_wick(df),
                    2
                ),

                # -----------------------
                # Relative Strength Benchmark
                # -----------------------

                "index_change": self.get_index_change(),

                # -----------------------
                # Delivery (NSE)
                # -----------------------

                "delivery_percentage": delivery["delivery_percentage"],

                "delivery_change": delivery["delivery_change"],

                # -----------------------
                # Open Interest (NSE, F&O symbols only)
                # -----------------------

                "oi_change": oi_change

            }

        except Exception as e:

            print(f"{symbol}: {e}")

            return None