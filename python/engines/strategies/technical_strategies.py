from engines.strategies.base_strategy import BaseStrategy


class TechnicalStrategy(BaseStrategy):
    """Rule-based daily technical setups using the scanner's existing fields."""

    SUPPORTED = (
        "Breakout with Volume",
        "Breakdown with Volume",
        "VWAP Momentum",
        "EMA 20/50 Crossover",
        "RSI Reversal",
        "Bollinger Band Breakout",
    )

    def __init__(self, strategy_name):
        if strategy_name not in self.SUPPORTED:
            raise ValueError(f"Unsupported technical strategy: {strategy_name}")
        self.strategy_name = strategy_name

    @staticmethod
    def _score(*parts):
        return min(100, sum(parts))

    @staticmethod
    def _signal(score):
        if score >= 80:
            return "Very Strong"
        if score >= 65:
            return "Strong"
        if score >= 50:
            return "Moderate"
        return "Weak"

    def _evaluate(self, stock):
        close, previous_close = stock.get("curr_close"), stock.get("prev_close")
        high, low = stock.get("curr_high"), stock.get("curr_low")
        volume_change = stock.get("volume_change") or 0
        price_change = stock.get("price_change") or 0
        vwap, previous_vwap = stock.get("vwap"), stock.get("prev_vwap")
        ema20, ema50 = stock.get("ema20"), stock.get("ema50")
        prev_ema20, prev_ema50 = stock.get("prev_ema20"), stock.get("prev_ema50")
        rsi, previous_rsi = stock.get("rsi"), stock.get("prev_rsi")
        upper_band = stock.get("bb_upper")

        if self.strategy_name == "Breakout with Volume":
            passed = bool(stock.get("breakout")) and volume_change >= 50 and price_change > 0
            score = self._score(40 if stock.get("breakout") else 0, 25 if volume_change >= 100 else 15 if volume_change >= 50 else 0, 20 if price_change >= 2 else 10 if price_change > 0 else 0, 15 if close is not None and vwap is not None and close > vwap else 0)
            direction, reason = 1, "20-day resistance breakout with volume"
        elif self.strategy_name == "Breakdown with Volume":
            passed = bool(stock.get("breakdown")) and volume_change >= 50 and price_change < 0
            score = self._score(40 if stock.get("breakdown") else 0, 25 if volume_change >= 100 else 15 if volume_change >= 50 else 0, 20 if price_change <= -2 else 10 if price_change < 0 else 0, 15 if close is not None and vwap is not None and close < vwap else 0)
            direction, reason = -1, "20-day support breakdown with volume"
        elif self.strategy_name == "VWAP Momentum":
            crossed_above = all(value is not None for value in (close, previous_close, vwap, previous_vwap)) and previous_close <= previous_vwap and close > vwap
            passed = bool(crossed_above) and volume_change >= 20
            score = self._score(45 if crossed_above else 0, 20 if volume_change >= 50 else 10 if volume_change >= 20 else 0, 20 if price_change >= 1 else 10 if price_change > 0 else 0, 15 if stock.get("trend") == "Bullish" else 0)
            direction, reason = 1, "price crossed above VWAP with momentum"
        elif self.strategy_name == "EMA 20/50 Crossover":
            crossed_above = all(value is not None for value in (ema20, ema50, prev_ema20, prev_ema50)) and prev_ema20 <= prev_ema50 and ema20 > ema50
            passed = bool(crossed_above) and close is not None and ema20 is not None and close > ema20
            score = self._score(55 if crossed_above else 0, 20 if close is not None and ema20 is not None and close > ema20 else 0, 15 if volume_change >= 50 else 5 if volume_change > 0 else 0, 10 if price_change > 0 else 0)
            direction, reason = 1, "EMA 20 crossed above EMA 50"
        elif self.strategy_name == "RSI Reversal":
            reversed_from_oversold = previous_rsi is not None and rsi is not None and previous_rsi <= 30 and rsi > 30
            passed = reversed_from_oversold and price_change > 0
            score = self._score(50 if reversed_from_oversold else 0, 20 if rsi is not None and rsi <= 50 else 10 if rsi is not None and rsi <= 60 else 0, 15 if price_change >= 1 else 8 if price_change > 0 else 0, 15 if volume_change >= 50 else 0)
            direction, reason = 1, "RSI reversed above the oversold threshold"
        else:  # Bollinger Band Breakout
            passed = close is not None and upper_band is not None and close > upper_band and volume_change >= 50
            score = self._score(50 if close is not None and upper_band is not None and close > upper_band else 0, 25 if volume_change >= 100 else 15 if volume_change >= 50 else 0, 15 if price_change >= 1 else 0, 10 if stock.get("trend") == "Bullish" else 0)
            direction, reason = 1, "close broke above the upper Bollinger Band"

        return passed, score, direction, reason, close, high, low

    def execute(self, stock):
        passed, score, direction, reason, close, high, low = self._evaluate(stock)
        stoploss = low if direction > 0 else high
        target = None
        if close is not None and stoploss is not None:
            target = round(close + direction * abs(close - stoploss) * 2, 2)

        return {
            "passed": passed and score >= 50,
            "strategy": self.strategy_name,
            "market_structure": "Bullish" if direction > 0 else "Bearish",
            "score": score,
            "raw_score": score,
            "signal": self._signal(score),
            "confidence": 90 if score >= 80 else 80 if score >= 65 else 70 if score >= 50 else 40,
            "risk": "Medium" if score >= 65 else "High",
            "entry": close,
            "stoploss": stoploss,
            "target": target,
            "reasons": [reason],
            "stock": stock,
        }
