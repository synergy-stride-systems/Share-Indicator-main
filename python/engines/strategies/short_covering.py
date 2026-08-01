from engines.strategies.base_strategy import BaseStrategy


class ShortCoveringStrategy(BaseStrategy):

    """
    Short Covering Detection Strategy

    Version 1
    """

    # --------------------------------------------------
    # CONFIGURATION
    # --------------------------------------------------

    WEIGHTS = {
        "price": 25,
        "volume": 20,
        "delivery": 15,
        "oi": 25,
        "relative_strength": 10,
        "trend": 5,
        "vwap": 5
    }

    MAX_RAW_SCORE = sum(WEIGHTS.values())  # 105

    SIGNAL_LEVELS = {
        80: "Very Strong",
        65: "Strong",
        50: "Moderate",
        35: "Weak",
        0: "No Signal"
    }

    def __init__(self):
        pass

    # --------------------------------------------------
    # PRICE MOMENTUM
    # --------------------------------------------------

    def calculate_price_score(self, stock):

        score = 0
        reasons = []

        change = stock.get("price_change")

        if change is None:
            reasons.append("Price Data Unavailable")
            return score, reasons

        if change >= 4:

            score = 25
            reasons.append("Very Strong Price Momentum")

        elif change >= 3:

            score = 22
            reasons.append("Strong Price Momentum")

        elif change >= 2:

            score = 18
            reasons.append("Good Price Momentum")

        elif change >= 1:

            score = 10
            reasons.append("Positive Price Movement")

        else:

            reasons.append("Weak Price Momentum")

        return score, reasons

    # --------------------------------------------------
    # VOLUME EXPANSION
    # --------------------------------------------------

    def calculate_volume_score(self, stock):

        score = 0
        reasons = []

        volume = stock.get("volume_change")

        if volume is None:
            reasons.append("Volume Data Unavailable")
            return score, reasons

        if volume >= 200:

            score = 20
            reasons.append("Huge Volume Expansion")

        elif volume >= 150:

            score = 17
            reasons.append("Strong Volume Expansion")

        elif volume >= 100:

            score = 14
            reasons.append("High Volume")

        elif volume >= 50:

            score = 8
            reasons.append("Moderate Volume Increase")

        else:

            reasons.append("Normal Volume")

        return score, reasons

    # --------------------------------------------------
    # TREND
    # --------------------------------------------------

    def calculate_trend_score(self, stock):

        score = 0
        reasons = []

        prev_close = stock.get("prev_close")
        curr_close = stock.get("curr_close")

        if prev_close is None or curr_close is None:
            return score, reasons

        if curr_close > prev_close:

            score = 5
            reasons.append("Up Trend")

        else:

            reasons.append("No Up Trend")

        return score, reasons

    # --------------------------------------------------
    # VWAP
    # --------------------------------------------------

    def calculate_vwap_score(self, stock):

        score = 0
        reasons = []

        vwap = stock.get("vwap")
        close = stock.get("curr_close")

        if vwap is None or close is None:
            return score, reasons

        if close > vwap:

            score = 5
            reasons.append("Trading Above VWAP")

        else:

            reasons.append("Below VWAP")

        return score, reasons

    # --------------------------------------------------
    # SIGNAL CLASSIFIER
    # --------------------------------------------------

    def classify_signal(self, score):

        # Single source of truth: reads from SIGNAL_LEVELS instead of
        # duplicating the same thresholds as separate if/elif branches.
        for threshold in sorted(self.SIGNAL_LEVELS.keys(), reverse=True):

            if score >= threshold:
                return self.SIGNAL_LEVELS[threshold]

        return "No Signal"

        # --------------------------------------------------
    # DELIVERY SCORE
    # --------------------------------------------------

    def calculate_delivery_score(self, stock):

        score = 0
        reasons = []

        delivery_percent = stock.get("delivery_percentage")
        delivery_change = stock.get("delivery_change")

        if delivery_percent is None and delivery_change is None:
            reasons.append("Delivery Data Unavailable")
            return score, reasons

        if delivery_percent is not None:

            if delivery_percent >= 70:
                score += 10
                reasons.append("Very High Delivery Percentage")

            elif delivery_percent >= 60:
                score += 8
                reasons.append("High Delivery Percentage")

            elif delivery_percent >= 45:
                score += 5
                reasons.append("Healthy Delivery Percentage")

        if delivery_change is not None:

            if delivery_change >= 50:
                score += 5
                reasons.append("Delivery Volume Increased Significantly")

            elif delivery_change >= 20:
                score += 3
                reasons.append("Delivery Volume Increasing")

        return score, reasons

    # --------------------------------------------------
    # OPEN INTEREST SCORE
    # --------------------------------------------------

    def calculate_oi_score(self, stock):

        score = 0
        reasons = []

        oi_change = stock.get("oi_change")

        if oi_change is None:
            reasons.append("OI Data Unavailable (Non-F&O or Not Fetched)")
            return score, reasons

        if oi_change <= -15:

            score = 25
            reasons.append("Massive OI Reduction")

        elif oi_change <= -10:

            score = 22
            reasons.append("Large OI Reduction")

        elif oi_change <= -5:

            score = 18
            reasons.append("OI Falling")

        elif oi_change <= -2:

            score = 10
            reasons.append("Slight OI Reduction")

        else:

            reasons.append("OI Not Supporting Short Covering")

        return score, reasons

    # --------------------------------------------------
    # RELATIVE STRENGTH
    # --------------------------------------------------

    def calculate_relative_strength(self, stock):

        score = 0
        reasons = []

        stock_return = stock.get("price_change")
        index_return = stock.get("index_change")

        # `.get(key, default)` only falls back when the key is MISSING.
        # Both fields exist on the stock dict but may hold `None`
        # (e.g. before market_data.py has real index data), so we
        # need an explicit None check rather than a `.get` default.
        if stock_return is None:
            reasons.append("Relative Strength Data Unavailable")
            return score, reasons

        if index_return is None:
            index_return = 0

        rs = stock_return - index_return

        if rs >= 3:

            score = 10
            reasons.append("Strong Relative Strength")

        elif rs >= 2:

            score = 8
            reasons.append("Outperforming Index")

        elif rs >= 1:

            score = 5
            reasons.append("Slightly Outperforming")

        else:

            reasons.append("No Relative Strength")

        return score, reasons

    # --------------------------------------------------
    # CONFIDENCE
    # --------------------------------------------------

    def calculate_confidence(self, total_score):

        if total_score >= 90:
            return 100

        if total_score >= 80:
            return 95

        if total_score >= 70:
            return 85

        if total_score >= 60:
            return 75

        if total_score >= 50:
            return 65

        return 40

    # --------------------------------------------------
    # RISK
    # --------------------------------------------------

    def calculate_risk(self, total_score):

        if total_score >= 85:
            return "Low"

        if total_score >= 70:
            return "Medium"

        return "High"

    # --------------------------------------------------
    # ENTRY PRICE
    # --------------------------------------------------

    def suggested_entry(self, stock):

        return stock.get("curr_close")

    # --------------------------------------------------
    # STOP LOSS
    # --------------------------------------------------

    def suggested_stoploss(self, stock):

        return stock.get("curr_low")

    # --------------------------------------------------
    # TARGET
    # --------------------------------------------------

    def suggested_target(self, stock):

        close = stock.get("curr_close")
        low = stock.get("curr_low")

        if close is None or low is None:
            return None

        risk = close - low

        return round(close + (risk * 2), 2)

        # --------------------------------------------------
    # EXECUTE STRATEGY
    # --------------------------------------------------

    def execute(self, stock):

        reasons = []

        # -------------------------------
        # Individual Scores
        # -------------------------------

        price_score, r = self.calculate_price_score(stock)
        reasons.extend(r)

        volume_score, r = self.calculate_volume_score(stock)
        reasons.extend(r)

        delivery_score, r = self.calculate_delivery_score(stock)
        reasons.extend(r)

        oi_score, r = self.calculate_oi_score(stock)
        reasons.extend(r)

        rs_score, r = self.calculate_relative_strength(stock)
        reasons.extend(r)

        trend_score, r = self.calculate_trend_score(stock)
        reasons.extend(r)

        vwap_score, r = self.calculate_vwap_score(stock)
        reasons.extend(r)

        # -------------------------------
        # Total Score
        # -------------------------------

        raw_score = (
            price_score +
            volume_score +
            delivery_score +
            oi_score +
            rs_score +
            trend_score +
            vwap_score
        )

        # Normalize to 100
        total_score = round((raw_score / self.MAX_RAW_SCORE) * 100)

        signal = self.classify_signal(total_score)

        confidence = self.calculate_confidence(total_score)

        risk = self.calculate_risk(total_score)

        entry = self.suggested_entry(stock)

        stoploss = self.suggested_stoploss(stock)

        target = self.suggested_target(stock)

        passed = total_score >= 50

        return {

            "passed": passed,

            "strategy": "Short Covering",

            "score": total_score,

            "raw_score": raw_score,

            "signal": signal,

            "confidence": confidence,

            "risk": risk,

            "entry": entry,

            "stoploss": stoploss,

            "target": target,

            "price_score": price_score,

            "volume_score": volume_score,

            "delivery_score": delivery_score,

            "oi_score": oi_score,

            "relative_strength_score": rs_score,

            "trend_score": trend_score,

            "vwap_score": vwap_score,

            "reasons": reasons,

            "stock": stock

        }