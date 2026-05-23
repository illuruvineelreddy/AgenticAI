from brokers.base import BaseBroker
from brokers.mock import MockBroker
from brokers.zerodha import ZerodhaBroker
from brokers.upstox import UpstoxBroker
from brokers.fyers import FyersBroker
from brokers.dhan import DhanBroker

def get_broker_client(broker_name: str) -> BaseBroker:
    """
    Factory function to instantiate the correct broker adapter.
    """
    name = broker_name.strip().lower()
    if name == "zerodha":
        return ZerodhaBroker()
    elif name == "upstox":
        return UpstoxBroker()
    elif name == "fyers":
        return FyersBroker()
    elif name == "dhan":
        return DhanBroker()
    elif name == "mock":
        return MockBroker()
    else:
        raise ValueError(f"Unknown broker name: {broker_name}")

__all__ = [
    "BaseBroker",
    "MockBroker",
    "ZerodhaBroker",
    "UpstoxBroker",
    "FyersBroker",
    "DhanBroker",
    "get_broker_client",
]
