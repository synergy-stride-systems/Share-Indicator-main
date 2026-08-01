from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest import result

from services.market_data import MarketDataService
from engines.strategy_manager import StrategyManager
from engines.strategies.condition_strategy import ConditionStrategy
from engines.strategies.short_covering import ShortCoveringStrategy
...
       


class ScannerEngine:

    def __init__(self, symbols, max_workers=3):
        self.symbols = symbols
        self.market_data = MarketDataService()
        self.max_workers = max_workers

    # -----------------------------------------------------
    # Scan One Stock
    # -----------------------------------------------------

    def scan_stock(self, symbol, conditions):

        try:

            stock = self.market_data.get_stock_data(symbol)


            if stock is None:
                return None

            manager = StrategyManager()

        # Existing Condition Strategy
            manager.register(
                ConditionStrategy(conditions)
         )

           
            manager.register(
                ShortCoveringStrategy()
        )

        # Future Strategies
        #
        # from engines.strategies.short_covering import ShortCoveringStrategy
        # manager.register(ShortCoveringStrategy())

            result = manager.execute(stock)

            if result is None:
                return None

        # Use metric calculated by MarketDataService
            stock["percent_gain"] = stock.get("price_change", 0)

            return stock

        except Exception as e:

            print(f"Scanner Error ({symbol}): {e}")

            return None
        
    
    
    # -----------------------------------------------------
    # Scan All Stocks
    # -----------------------------------------------------

    def scan(self, conditions, progress_callback=None):

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
                    conditions
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
                        results.append(result)

                except Exception as e:

                    print(f"{symbol}: {e}")

        # Sort highest gain first
        results.sort(
            key=lambda x: x.get("percent_gain", 0),
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