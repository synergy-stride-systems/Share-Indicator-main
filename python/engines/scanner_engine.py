from concurrent.futures import ThreadPoolExecutor, as_completed
from services.market_data import MarketDataService
from engines.strategies.condition_strategy import ConditionStrategy
from engines.strategies.short_covering import ShortCoveringStrategy
from engines.strategies.positioning_strategies import PositioningStrategy
from engines.strategies.technical_strategies import TechnicalStrategy


class ScannerEngine:

    POSITIONING_STRATEGIES = (
        "Short Covering",
        "Long Build-up",
        "Short Build-up",
        "Long Unwinding",
    )
    TECHNICAL_STRATEGIES = TechnicalStrategy.SUPPORTED
    ALL_STRATEGIES = POSITIONING_STRATEGIES + TECHNICAL_STRATEGIES

    def __init__(self, symbols, max_workers=30):
        self.symbols = symbols
        self.market_data = MarketDataService()
        self.max_workers = max_workers

    # -----------------------------------------------------
    # Scan One Stock
    # -----------------------------------------------------

    def scan_stock(
        self,
        symbol,
        conditions,
        mode="condition",
        strategy_name="Short Covering",
        minimum_score=0,
    ):

        try:

            stock = self.market_data.get_stock_data(symbol)


            if stock is None:
                return None

            if mode == "strategy":
                selected_names = (
                    self.ALL_STRATEGIES
                    if strategy_name == "All Strategies"
                    else (strategy_name,)
                )
                matches = []
                for name in selected_names:
                    if name == "Short Covering":
                        strategy = ShortCoveringStrategy()
                    elif name in self.TECHNICAL_STRATEGIES:
                        strategy = TechnicalStrategy(name)
                    else:
                        strategy = PositioningStrategy(name)
                    result = strategy.execute(stock)
                    if not result["passed"] or result["score"] < minimum_score:
                        continue

                    # Flatten each matching strategy so the SSE consumer can
                    # render one row per symbol/setup combination.
                    strategy_fields = {key: value for key, value in result.items() if key != "stock"}
                    matches.append({
                        **stock,
                        **strategy_fields,
                        "percent_gain": stock.get("price_change", 0),
                    })
                return matches or None

            result = ConditionStrategy(conditions).execute(stock)
            if result is None:
                return None

            stock["percent_gain"] = stock.get("price_change", 0)
            return stock

        except Exception as e:

            print(f"Scanner Error ({symbol}): {e}")

            return None
        
    
    
    # -----------------------------------------------------
    # Scan All Stocks
    # -----------------------------------------------------

    def scan(
        self,
        conditions,
        progress_callback=None,
        mode="condition",
        strategy_name="Short Covering",
        minimum_score=0,
    ):

        results = []

        total = len(self.symbols)

        completed = 0

        with ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:

            futures = {

                executor.submit(
                    self.scan_stock,
                    symbol,
                    conditions,
                    mode,
                    strategy_name,
                    minimum_score,
                ): symbol

                for symbol in self.symbols

            }

            for future in as_completed(futures):

                completed += 1

                symbol = futures[future]

                # Progress callback
                if progress_callback:

                    progress_callback(
                        current=completed,
                        total=total,
                        symbol=symbol
                    )

                try:

                    result = future.result()

                    if result:
                        results.extend(result if isinstance(result, list) else [result])

                except Exception as e:

                    print(f"{symbol}: {e}")

        # Highest-confidence strategies first, with price change as a tiebreaker.
        results.sort(
            key=lambda x: (x.get("score", 0), x.get("percent_gain", 0)),
            reverse=True
        )

        return results

    # -----------------------------------------------------
    # Summary
    # -----------------------------------------------------

    def summary(self, results):

        if not results:

            return {
                "total_signals": 0,
                "highest_gain": 0,
                "lowest_gain": 0
            }

        highest = max(
            results,
            key=lambda x: x["percent_gain"]
        )

        lowest = min(
            results,
            key=lambda x: x["percent_gain"]
        )

        return {

            "total_signals": len(results),

            "highest_symbol": highest["symbol"],

            "highest_gain": highest["percent_gain"],

            "lowest_symbol": lowest["symbol"],

            "lowest_gain": lowest["percent_gain"]

        }
