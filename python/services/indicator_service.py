import pandas as pd
import numpy as np


class IndicatorService:

    # =====================================================
    # PRICE CHANGE %
    # =====================================================

    @staticmethod
    def price_change(df):

        return df["Close"].pct_change() * 100

    # =====================================================
    # VOLUME CHANGE %
    # =====================================================

    @staticmethod
    def volume_change(df):

        avg_volume = df["Volume"].rolling(20).mean()

        return ((df["Volume"] - avg_volume) / avg_volume) * 100

    # =====================================================
    # SIMPLE MOVING AVERAGE
    # =====================================================

    @staticmethod
    def sma(df, period):

        return df["Close"].rolling(period).mean()

    # =====================================================
    # EXPONENTIAL MOVING AVERAGE
    # =====================================================

    @staticmethod
    def ema(df, period):

        return df["Close"].ewm(span=period, adjust=False).mean()

    # =====================================================
    # VWAP
    # =====================================================

    @staticmethod
    def vwap(df):

        typical_price = (

            df["High"]

            + df["Low"]

            + df["Close"]

        ) / 3

        cumulative_tp_volume = (

            typical_price * df["Volume"]

        ).cumsum()

        cumulative_volume = df["Volume"].cumsum()

        return cumulative_tp_volume / cumulative_volume

    # =====================================================
    # RSI
    # =====================================================

    @staticmethod
    def rsi(df, period=14):

        delta = df["Close"].diff()

        gain = delta.where(delta > 0, 0)

        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(period).mean()

        avg_loss = loss.rolling(period).mean()

        rs = avg_gain / avg_loss

        return 100 - (100 / (1 + rs))

    # =====================================================
    # MACD
    # =====================================================

    @staticmethod
    def macd(df):

        ema12 = IndicatorService.ema(df, 12)

        ema26 = IndicatorService.ema(df, 26)

        macd = ema12 - ema26

        signal = macd.ewm(span=9, adjust=False).mean()

        histogram = macd - signal

        return macd, signal, histogram

    # =====================================================
    # ATR
    # =====================================================

    @staticmethod
    def atr(df, period=14):

        high_low = df["High"] - df["Low"]

        high_close = (

            df["High"]

            - df["Close"].shift()

        ).abs()

        low_close = (

            df["Low"]

            - df["Close"].shift()

        ).abs()

        ranges = pd.concat(

            [high_low, high_close, low_close],

            axis=1

        )

        true_range = ranges.max(axis=1)

        return true_range.rolling(period).mean()

    # =====================================================
    # BOLLINGER BANDS
    # =====================================================

    @staticmethod
    def bollinger(df, period=20):

        sma = IndicatorService.sma(df, period)

        std = df["Close"].rolling(period).std()

        upper = sma + (2 * std)

        lower = sma - (2 * std)

        return upper, sma, lower

    # =====================================================
    # HIGHEST HIGH
    # =====================================================

    @staticmethod
    def highest(df, period):

        return df["High"].rolling(period).max()

    # =====================================================
    # LOWEST LOW
    # =====================================================

    @staticmethod
    def lowest(df, period):

        return df["Low"].rolling(period).min()

    # =====================================================
    # GAP %
    # =====================================================

    @staticmethod
    def gap(df):

        return (

            (

                df["Open"]

                - df["Close"].shift()

            )

            /

            df["Close"].shift()

        ) * 100

    # =====================================================
    # VOLUME SMA
    # =====================================================

    @staticmethod
    def volume_sma(df, period=20):

        return df["Volume"].rolling(period).mean()

    # =====================================================
    # VOLUME SPIKE %
    # =====================================================

    @staticmethod
    def volume_spike(df):

        average = IndicatorService.volume_sma(df)

        return (

            (

                df["Volume"]

                - average

            )

            /

            average

        ) * 100

    # =====================================================
    # RELATIVE STRENGTH
    # =====================================================

    @staticmethod
    def relative_strength(stock_return, index_return):

        return stock_return - index_return

    # =====================================================
    # TREND
    # =====================================================

    @staticmethod
    def trend(df):

        ema20 = IndicatorService.ema(df, 20)

        ema50 = IndicatorService.ema(df, 50)

        latest20 = ema20.iloc[-1]

        latest50 = ema50.iloc[-1]

        if latest20 > latest50:

            return "Bullish"

        elif latest20 < latest50:

            return "Bearish"

        return "Sideways"

    # =====================================================
    # VOLATILITY
    # =====================================================

    @staticmethod
    def volatility(df):

        return (

            df["Close"]

            .pct_change()

            .rolling(20)

            .std()

        ) * 100

    # =====================================================
    # BREAKOUT
    # =====================================================

    @staticmethod
    def breakout(df):

        resistance = df["High"].rolling(20).max()

        latest_close = df["Close"].iloc[-1]

        return latest_close > resistance.iloc[-2]

    # =====================================================
    # BREAKDOWN
    # =====================================================

    @staticmethod
    def breakdown(df):

        support = df["Low"].rolling(20).min()

        latest_close = df["Close"].iloc[-1]

        return latest_close < support.iloc[-2]

    # =====================================================
    # CANDLE BODY %
    # =====================================================

    @staticmethod
    def candle_body(df):

        latest = df.iloc[-1]

        body = abs(

            latest["Close"]

            - latest["Open"]

        )

        total = (

            latest["High"]

            - latest["Low"]

        )

        if total == 0:

            return 0

        return (body / total) * 100

    # =====================================================
    # UPPER WICK %
    # =====================================================

    @staticmethod
    def upper_wick(df):

        latest = df.iloc[-1]

        return (

            latest["High"]

            - max(

                latest["Open"],

                latest["Close"]

            )

        )

    # =====================================================
    # LOWER WICK %
    # =====================================================

    @staticmethod
    def lower_wick(df):

        latest = df.iloc[-1]

        return (

            min(

                latest["Open"],

                latest["Close"]

            )

            - latest["Low"]

        )

    # =====================================================
    # SHARPE RATIO (For Backtesting)
    # =====================================================

    @staticmethod
    def sharpe_ratio(returns, risk_free_rate=0):

        excess = returns - risk_free_rate

        if excess.std() == 0:

            return 0

        return (

            np.sqrt(252)

            * excess.mean()

            / excess.std()

        )