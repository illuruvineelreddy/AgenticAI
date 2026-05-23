from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseBroker(ABC):
    """
    Abstract Base Class for all broker integrations (Zerodha, Upstox, Fyers, Dhan, Mock).
    """

    @abstractmethod
    async def connect(self) -> bool:
        """Initialize connection/session with the broker."""
        pass
        
    @abstractmethod
    async def disconnect(self) -> bool:
        """Close connection/session with the broker."""
        pass

    @abstractmethod
    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        """Fetch the latest quote/LTP for a symbol."""
        pass

    @abstractmethod
    async def place_order(
        self, 
        symbol: str, 
        side: str, 
        quantity: int, 
        order_type: str, 
        price: Optional[float] = None, 
        trigger_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """Place an order with the broker."""
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order."""
        pass

    @abstractmethod
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Fetch current open positions."""
        pass

    @abstractmethod
    async def get_orders(self) -> List[Dict[str, Any]]:
        """Fetch all orders (completed and pending) for the day."""
        pass

    @abstractmethod
    async def get_historical_data(
        self, 
        symbol: str, 
        interval: str, 
        from_date: str, 
        to_date: str
    ) -> List[Dict[str, Any]]:
        """Fetch historical candle/bar data."""
        pass
