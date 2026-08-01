from typing import List


class StrategyManager:

    def __init__(self):

        self.strategies: List = []

    # ====================================================
    # Register
    # ====================================================

    def register(self, strategy):

        self.strategies.append(strategy)

    # ====================================================
    # Remove
    # ====================================================

    def unregister(self, strategy):

        if strategy in self.strategies:
            self.strategies.remove(strategy)

    # ====================================================
    # Clear
    # ====================================================

    def clear(self):

        self.strategies.clear()

    # ====================================================
    # List
    # ====================================================

    def list_strategies(self):

        return [

            strategy.__class__.__name__

            for strategy in self.strategies

        ]

    # ====================================================
    # Count
    # ====================================================

    def count(self):

        return len(self.strategies)

    # ====================================================
    # Execute Sequentially
    #
    # Used by Condition Scanner
    # ====================================================

    def execute(self, stock):

        result = stock

        for strategy in self.strategies:

            result = strategy.execute(result)

            if result is None:
                return None

        return result

    # ====================================================
    # Execute Every Strategy Independently
    #
    # Used by Strategy Scanner
    # ====================================================

    def execute_all(self, stock):

        outputs = []

        for strategy in self.strategies:

            try:

                result = strategy.execute(stock)

                outputs.append({

                    "strategy": strategy.__class__.__name__,

                    "result": result,

                    "passed": (

                        result is not None

                        and

                        result.get("passed", False)

                        if isinstance(result, dict)

                        else result is not None

                    )

                })

            except Exception as e:

                outputs.append({

                    "strategy": strategy.__class__.__name__,

                    "passed": False,

                    "error": str(e)

                })

        return outputs

    # ====================================================
    # Best Strategy
    #
    # Highest Score Wins
    # ====================================================

    def execute_best(self, stock):

        best = None

        highest = -1

        for strategy in self.strategies:

            try:

                result = strategy.execute(stock)

                if not result:
                    continue

                score = result.get("score", 0)

                if score > highest:

                    highest = score

                    best = result

            except Exception:

                pass

        return best

    # ====================================================
    # Execute Specific Strategy
    # ====================================================

    def execute_strategy(

        self,

        strategy_name,

        stock

    ):

        for strategy in self.strategies:

            if (

                strategy.__class__.__name__

                ==

                strategy_name

            ):

                return strategy.execute(stock)

        return None