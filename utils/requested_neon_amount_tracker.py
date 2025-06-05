from decimal import Decimal
from functools import wraps


class AmountTracker:
    def __init__(self):
        self.total_spent = Decimal(0)

    def add(self, amount):
        self.total_spent += Decimal(amount)

    def get_total(self):
        return self.total_spent


# Глобальный экземпляр
amount_tracker = AmountTracker()


def track_spent_amount(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        amount = kwargs.get("amount")
        if amount is None and len(args) > 3:
            amount = args[3]  # предполагается, что amount 3-й аргумент
        if amount is not None:
            amount_tracker.add(amount)
        return func(*args, **kwargs)

    return wrapper
