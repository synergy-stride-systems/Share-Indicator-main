from engines.strategies.base_strategy import BaseStrategy


class PositioningStrategy(BaseStrategy):
    """Score the standard futures price/OI positioning strategies.

    Delivery measures cash-market participation, not futures positions.  It is
    therefore confirmation only: accumulation helps bullish strategies while
    weak/reducing delivery can confirm distribution-led bearish strategies.
    """

    CONFIG = {
        "Long Build-up": {"price_direction": 1, "oi_direction": 1, "delivery_mode": "accumulation"},
        "Short Build-up": {"price_direction": -1, "oi_direction": 1, "delivery_mode": "distribution"},
        "Long Unwinding": {"price_direction": -1, "oi_direction": -1, "delivery_mode": "distribution"},
    }

    def __init__(self, strategy_name):
        if strategy_name not in self.CONFIG:
            raise ValueError(f"Unsupported strategy: {strategy_name}")
        self.strategy_name = strategy_name
        self.config = self.CONFIG[strategy_name]

    @staticmethod
    def _direction_score(value, direction, maximum=25):
        """Score a percentage move only when it agrees with the setup."""
        if value is None or value * direction <= 0:
            return 0
        magnitude = abs(value)
        if magnitude >= 4:
            return maximum
        if magnitude >= 3:
            return round(maximum * 0.88)
        if magnitude >= 2:
            return round(maximum * 0.72)
        if magnitude >= 1:
            return round(maximum * 0.40)
        return 0

    @staticmethod
    def _volume_score(volume_change):
        if volume_change is None:
            return 0
        if volume_change >= 200:
            return 20
        if volume_change >= 150:
            return 17
        if volume_change >= 100:
            return 14
        if volume_change >= 50:
            return 8
        return 0

    @staticmethod
    def _accumulation_delivery_score(quantity_change, percentage):
        """Cash delivery confirmation for bullish positioning."""
        quantity_score = (
            15 if quantity_change is not None and quantity_change >= 100 else
            12 if quantity_change is not None and quantity_change >= 50 else
            8 if quantity_change is not None and quantity_change >= 20 else
            4 if quantity_change is not None and quantity_change > 0 else 0
        )
        percentage_score = (
            10 if percentage is not None and percentage >= 70 else
            8 if percentage is not None and percentage >= 60 else
            5 if percentage is not None and percentage >= 45 else 0
        )
        return quantity_score, percentage_score

    @staticmethod
    def _distribution_delivery_score(quantity_change, percentage):
        """Absence of cash accumulation is only a modest bearish confirmation."""
        quantity_score = (
            10 if quantity_change is not None and quantity_change <= -30 else
            6 if quantity_change is not None and quantity_change < 0 else 0
        )
        percentage_score = (
            6 if percentage is not None and percentage <= 30 else
            3 if percentage is not None and percentage <= 45 else 0
        )
        return quantity_score, percentage_score

    @staticmethod
    def _signal(score):
        if score >= 80:
            return "Very Strong"
        if score >= 65:
            return "Strong"
        if score >= 50:
            return "Moderate"
        if score >= 35:
            return "Weak"
        return "No Signal"

    @staticmethod
    def _confidence(score):
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
        price_change = stock.get("price_change")
        oi_change = stock.get("oi_change")
        price_direction = self.config["price_direction"]
        oi_direction = self.config["oi_direction"]

        price_score = self._direction_score(price_change, price_direction)
        oi_score = self._direction_score(oi_change, oi_direction)
        volume_score = self._volume_score(stock.get("volume_change"))

        if self.config["delivery_mode"] == "accumulation":
            delivery_volume_score, delivery_percentage_score = self._accumulation_delivery_score(
                stock.get("delivery_quantity_change"), stock.get("delivery_percentage")
            )
        else:
            delivery_volume_score, delivery_percentage_score = self._distribution_delivery_score(
                stock.get("delivery_quantity_change"), stock.get("delivery_percentage")
            )

        index_change = stock.get("index_change") or 0
        relative_strength = price_change - index_change if price_change is not None else None
        relative_strength_score = self._direction_score(relative_strength, price_direction, maximum=5)
        score = sum((price_score, oi_score, volume_score, delivery_volume_score,
                     delivery_percentage_score, relative_strength_score))

        setup_matches = (
            price_change is not None and oi_change is not None
            and price_change * price_direction > 0
            and oi_change * oi_direction > 0
        )

        close, low, high = stock.get("curr_close"), stock.get("curr_low"), stock.get("curr_high")
        if price_direction > 0:
            stoploss = low
            target = round(close + ((close - low) * 2), 2) if close is not None and low is not None else None
        else:
            stoploss = high
            target = round(close - ((high - close) * 2), 2) if close is not None and high is not None else None

        return {
            "passed": setup_matches and score >= 50,
            "strategy": self.strategy_name,
            "market_structure": self.strategy_name,
            "score": score,
            "raw_score": score,
            "signal": self._signal(score),
            "confidence": self._confidence(score),
            "risk": "Low" if score >= 85 else "Medium" if score >= 70 else "High",
            "entry": close,
            "stoploss": stoploss,
            "target": target,
            "price_score": price_score,
            "oi_score": oi_score,
            "volume_score": volume_score,
            "delivery_volume_score": delivery_volume_score,
            "delivery_percentage_score": delivery_percentage_score,
            "relative_strength_score": relative_strength_score,
            "reasons": [f"Price/OI setup: {self.strategy_name}"] + (
                ["Cash delivery confirms accumulation"] if self.config["delivery_mode"] == "accumulation"
                else ["Cash delivery is used as a distribution confirmation"]
            ),
            "stock": stock,
        }
