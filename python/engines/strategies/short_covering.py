from engines.strategies.base_strategy import BaseStrategy


class ShortCoveringStrategy(BaseStrategy):
    """End-of-day short-covering signal engine for NSE F&O stocks."""

    # Matches the proposed 100-point model exactly.
    WEIGHTS = {
        "price": 25,
        "oi": 25,
        "volume": 20,
        "delivery_volume": 15,
        "delivery_percentage": 10,
        "relative_strength": 5,
    }

    SIGNAL_LEVELS = {
        80: "Very Strong",
        65: "Strong",
        50: "Moderate",
        35: "Weak",
        0: "No Signal",
    }

    def classify_market_structure(self, stock):
        price_change = stock.get("price_change")
        oi_change = stock.get("oi_change")

        if price_change is None or oi_change is None:
            return "Insufficient Futures Data"
        if price_change > 0 and oi_change < 0:
            return "Short Covering"
        if price_change > 0 and oi_change > 0:
            return "Long Build-up"
        if price_change < 0 and oi_change < 0:
            return "Long Unwinding"
        if price_change < 0 and oi_change > 0:
            return "Short Build-up"
        return "Neutral"

    def calculate_price_score(self, stock):
        change = stock.get("price_change")
        if change is None:
            return 0, ["Price data unavailable"]
        if change >= 4:
            return 25, ["Very strong price momentum"]
        if change >= 3:
            return 22, ["Strong price momentum"]
        if change >= 2:
            return 18, ["Good price momentum"]
        if change >= 1:
            return 10, ["Positive price movement"]
        return 0, ["Weak price momentum"]

    def calculate_oi_score(self, stock):
        change = stock.get("oi_change")
        if change is None:
            return 0, ["Futures OI data unavailable"]
        if change <= -15:
            return 25, ["Massive futures OI reduction"]
        if change <= -10:
            return 22, ["Large futures OI reduction"]
        if change <= -5:
            return 18, ["Futures OI falling"]
        if change <= -2:
            return 10, ["Slight futures OI reduction"]
        return 0, ["OI is not supporting short covering"]

    def calculate_volume_score(self, stock):
        change = stock.get("volume_change")
        if change is None:
            return 0, ["Volume data unavailable"]
        if change >= 200:
            return 20, ["Huge volume expansion"]
        if change >= 150:
            return 17, ["Strong volume expansion"]
        if change >= 100:
            return 14, ["High volume"]
        if change >= 50:
            return 8, ["Moderate volume increase"]
        return 0, ["No meaningful volume expansion"]

    def calculate_delivery_volume_score(self, stock):
        change = stock.get("delivery_quantity_change")
        if change is None:
            return 0, ["Delivery quantity data unavailable"]
        if change >= 100:
            return 15, ["Delivery quantity more than doubled"]
        if change >= 50:
            return 12, ["Strong delivery quantity expansion"]
        if change >= 20:
            return 8, ["Delivery quantity increasing"]
        if change > 0:
            return 4, ["Delivery quantity slightly higher"]
        return 0, ["Delivery quantity is not increasing"]

    def calculate_delivery_percentage_score(self, stock):
        percentage = stock.get("delivery_percentage")
        if percentage is None:
            return 0, ["Delivery percentage unavailable"]
        if percentage >= 70:
            return 10, ["Very high delivery percentage"]
        if percentage >= 60:
            return 8, ["High delivery percentage"]
        if percentage >= 45:
            return 5, ["Healthy delivery percentage"]
        return 0, ["Low delivery percentage"]

    def calculate_relative_strength_score(self, stock):
        stock_return = stock.get("price_change")
        index_return = stock.get("index_change")
        if stock_return is None:
            return 0, ["Relative strength data unavailable"]

        relative_strength = stock_return - (index_return or 0)
        if relative_strength >= 3:
            return 5, ["Strong relative strength versus NIFTY"]
        if relative_strength >= 2:
            return 4, ["Outperforming NIFTY"]
        if relative_strength >= 1:
            return 2, ["Slightly outperforming NIFTY"]
        return 0, ["No relative strength"]

    def classify_signal(self, score):
        for threshold, label in sorted(self.SIGNAL_LEVELS.items(), reverse=True):
            if score >= threshold:
                return label
        return "No Signal"

    @staticmethod
    def confidence_for(score):
        if score >= 90:
            return 100
        if score >= 80:
            return 95
        if score >= 70:
            return 85
        if score >= 60:
            return 75
        if score >= 50:
            return 65
        return 40

    def execute(self, stock):
        market_structure = self.classify_market_structure(stock)

        scores = {}
        reasons = []
        calculators = {
            "price": self.calculate_price_score,
            "oi": self.calculate_oi_score,
            "volume": self.calculate_volume_score,
            "delivery_volume": self.calculate_delivery_volume_score,
            "delivery_percentage": self.calculate_delivery_percentage_score,
            "relative_strength": self.calculate_relative_strength_score,
        }

        for name, calculator in calculators.items():
            scores[name], messages = calculator(stock)
            reasons.extend(messages)

        score = sum(scores.values())
        signal = self.classify_signal(score)
        passed = market_structure == "Short Covering" and score >= 50

        close = stock.get("curr_close")
        low = stock.get("curr_low")
        target = None
        if close is not None and low is not None:
            target = round(close + ((close - low) * 2), 2)

        return {
            "passed": passed,
            "strategy": "Short Covering",
            "market_structure": market_structure,
            "score": score,
            "raw_score": score,
            "signal": signal,
            "confidence": self.confidence_for(score),
            "risk": "Low" if score >= 85 else "Medium" if score >= 70 else "High",
            "entry": close,
            "stoploss": low,
            "target": target,
            "price_score": scores["price"],
            "oi_score": scores["oi"],
            "volume_score": scores["volume"],
            "delivery_volume_score": scores["delivery_volume"],
            "delivery_percentage_score": scores["delivery_percentage"],
            "relative_strength_score": scores["relative_strength"],
            "reasons": reasons,
            "stock": stock,
        }
