from abc import ABC, abstractmethod

class BaseStrategy:

    @abstractmethod
    def execute(self, stock):
        pass