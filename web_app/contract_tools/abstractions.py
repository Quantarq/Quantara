from abc import ABC, abstractmethod

class BaseOnChainCaller(ABC):
    """A base class for all on chain callers"""

    @abstractmethod
    def get_on_chain_caller(self):
        """An abstract method to get on chain caller"""
        pass
