from .base_strategy import BaseStrategy


class ConditionStrategy(BaseStrategy):
    """
    Strategy that evaluates user-defined conditions.

    Example condition:

    {
        "lhs": "curr_close",
        "op": ">",
        "rhs": "prev_close",
        "conn": "and"
    }
    """

    def __init__(self, conditions=None):
        self.conditions = conditions or []

    def execute(self, stock):
        """
        Returns:
            stock  -> if all conditions pass
            None   -> if conditions fail
        """

        if not self.conditions:
            return stock

        if self.evaluate_conditions(stock):
            return stock

        return None

    # ---------------------------------------------------
    # Evaluate single condition
    # ---------------------------------------------------

    def evaluate_condition(self, stock, cond):

        lhs = stock.get(cond["lhs"])

        rhs_field = cond["rhs"]

        # rhs may be literal number
        if isinstance(rhs_field, (int, float)):
            rhs = rhs_field
        else:
            rhs = stock.get(rhs_field)

        if lhs is None or rhs is None:
            return False

        operator = cond["op"]

        if operator == "<":
            return lhs < rhs

        elif operator == ">":
            return lhs > rhs

        elif operator == "<=":
            return lhs <= rhs

        elif operator == ">=":
            return lhs >= rhs

        elif operator == "==":
            return lhs == rhs

        elif operator == "!=":
            return lhs != rhs

        return False

    # ---------------------------------------------------
    # Evaluate complete rule list
    # ---------------------------------------------------

    def evaluate_conditions(self, stock):

        groups = []
        current_group = []

        for i, cond in enumerate(self.conditions):

            current_group.append(cond)

            if (
                i == len(self.conditions) - 1
                or cond.get("conn") == "or"
            ):
                groups.append(current_group)
                current_group = []

        # OR between groups
        for group in groups:

            passed = True

            for condition in group:

                if not self.evaluate_condition(stock, condition):
                    passed = False
                    break

            if passed:
                return True

        return False

    # ---------------------------------------------------
    # Utility
    # ---------------------------------------------------

    @staticmethod
    def references_field(conditions, field_name):
        """
        Returns True if any condition references the field.

        Used for expensive calculations like sentiment,
        delivery, OI etc.
        """

        for cond in conditions:

            if cond.get("lhs") == field_name:
                return True

            rhs = cond.get("rhs")

            if isinstance(rhs, str) and rhs == field_name:
                return True

        return False