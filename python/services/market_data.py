import yfinance as yf
from datetime import datetime, timedelta

from services.indicator_service import IndicatorService


class MarketDataService:

    def get_stock_data(self, symbol):

        try:

            ticker = yf.Ticker(symbol)

            end = datetime.today()

            start = end - timedelta(days=120)

            df = ticker.history(
                start=start,
                end=end,
                auto_adjust=False
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

                "breakout": IndicatorService.breakout(df),

                "breakdown": IndicatorService.breakdown(df),

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

                # ===================================================
                # Future Fields (To be added later)
                # ===================================================

                "delivery_percentage": None,

                "delivery_change": None,

                "oi_change": None,

                "index_change": None

            }

        except Exception as e:

            print(f"{symbol}: {e}")

            return None