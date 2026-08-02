import threading
from datetime import datetime, timedelta

import yfinance as yf

from services.indicator_service import IndicatorService
from services.nse_data import NSEDataService


class MarketDataService:
    def __init__(self):
        self.nse = NSEDataService()
        self._index_change_cache = None
        self._index_change_cache_date = None
        self._index_lock = threading.Lock()

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
                    start=start,
                    end=end,
                    auto_adjust=False,
                )

                if index_df.empty or len(index_df) < 2:
                    return None

                index_change = IndicatorService.price_change(
                    index_df,
                ).iloc[-1]

                if index_change is None:
                    return None

                index_change = round(float(index_change), 2)

                self._index_change_cache = index_change
                self._index_change_cache_date = today

                return index_change

            except Exception as error:
                print(f"Index change fetch error: {error}")
                return None

    def get_stock_data(self, symbol):
        try:
            ticker = yf.Ticker(symbol)

            end = datetime.today()
            start = end - timedelta(days=120)

            df = ticker.history(
                start=start,
                end=end,
                auto_adjust=False,
            )

            if df.empty or len(df) < 50:
                return None

            if hasattr(df.columns, "levels"):
                df.columns = df.columns.get_level_values(0)

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

            macd, signal, histogram = IndicatorService.macd(df)

            df["MACD"] = macd
            df["MACDSignal"] = signal
            df["MACDHistogram"] = histogram

            prev = df.iloc[-2]
            curr = df.iloc[-1]

            market_date = (
                curr.name.date()
                if hasattr(curr.name, "date")
                else curr.name
            )

            delivery = self.nse.get_delivery_data(
                symbol,
                as_of_date=market_date,
            )

            # The scanner receives its universe dynamically from NSE,
            # so each scanned symbol is expected to be F&O eligible.
            oi_data = self.nse.get_oi_data(
                symbol,
                as_of_date=market_date,
            )

            return {
                "symbol": symbol,
                "market_date": str(market_date),

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

                "price_change": round(float(curr["PriceChange"]), 2),
                "volume_change": round(float(curr["VolumeChange"]), 2),

                "ema20": round(float(curr["EMA20"]), 2),
                "prev_ema20": round(float(prev["EMA20"]), 2),

                "ema50": round(float(curr["EMA50"]), 2),
                "prev_ema50": round(float(prev["EMA50"]), 2),

                "sma20": round(float(curr["SMA20"]), 2),

                "vwap": round(float(curr["VWAP"]), 2),
                "prev_vwap": round(float(prev["VWAP"]), 2),

                "rsi": round(float(curr["RSI"]), 2),
                "prev_rsi": round(float(prev["RSI"]), 2),

                "atr": round(float(curr["ATR"]), 2),
                "volume_spike": round(float(curr["VolumeSpike"]), 2),

                "macd": round(float(curr["MACD"]), 2),
                "macd_signal": round(float(curr["MACDSignal"]), 2),
                "macd_histogram": round(float(curr["MACDHistogram"]), 2),

                "bb_upper": round(float(curr["BBUpper"]), 2),
                "bb_middle": round(float(curr["BBMiddle"]), 2),
                "bb_lower": round(float(curr["BBLower"]), 2),

                "trend": IndicatorService.trend(df),
                "breakout": bool(IndicatorService.breakout(df)),
                "breakdown": bool(IndicatorService.breakdown(df)),

                "volatility": round(
                    float(IndicatorService.volatility(df).iloc[-1]),
                    2,
                ),

                "gap": round(
                    float(IndicatorService.gap(df).iloc[-1]),
                    2,
                ),

                "candle_body": round(
                    IndicatorService.candle_body(df),
                    2,
                ),

                "upper_wick": round(
                    IndicatorService.upper_wick(df),
                    2,
                ),

                "lower_wick": round(
                    IndicatorService.lower_wick(df),
                    2,
                ),

                "index_change": self.get_index_change(),

                "delivery_percentage": delivery["delivery_percentage"],
                "delivery_change": delivery["delivery_change"],
                "delivery_quantity": delivery["delivery_quantity"],
                "delivery_quantity_change": delivery[
                    "delivery_quantity_change"
                ],

                "oi_change": oi_data["oi_change"],
                "oi_status": oi_data["oi_status"],
            }

        except Exception as error:
            print(f"{symbol}: {error}")
            return None