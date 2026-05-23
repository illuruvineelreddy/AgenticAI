import asyncio
import time
import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from brokers.base import BaseBroker

class MockBroker(BaseBroker):
    """
    Mock broker that simulates live order placement, ticks, positions, and quotes.
    Used for local paper trading/testing when API keys are absent.
    """
    
    def __init__(self):
        self._connected = False
        self._orders: Dict[str, Dict[str, Any]] = {}
        self._positions: Dict[str, Dict[str, Any]] = {}
        
        # Base prices for mock tickers
        self._base_prices = {
            "RELIANCE": 2500.0,
            "TCS": 3600.0,
            "HDFCBANK": 1600.0,
            "INFY": 1450.0,
            "ICICIBANK": 950.0,
            "SBIN": 750.0,
            "ITC": 430.0,
            "NIFTY 50": 22000.0,
            "NIFTY BANK": 47000.0,
        }

    async def connect(self) -> bool:
        self._connected = True
        return True

    async def disconnect(self) -> bool:
        self._connected = False
        return True

    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        base_price = self._base_prices.get(symbol, 150.0)
        # Random change within +/- 0.5%
        fluctuation = base_price * random.uniform(-0.005, 0.005)
        price = round(base_price + fluctuation, 2)
        
        return {
            "symbol": symbol,
            "exchange": "NSE",
            "last_price": price,
            "volume": random.randint(1000, 100000),
            "buy_demand": random.randint(10000, 50000),
            "sell_demand": random.randint(10000, 50000),
            "ohlc": {
                "open": round(base_price, 2),
                "high": round(base_price * 1.01, 2),
                "low": round(base_price * 0.99, 2),
                "close": price
            },
            "timestamp": time.time()
        }

    async def place_order(
        self, 
        symbol: str, 
        side: str, 
        quantity: int, 
        order_type: str, 
        price: Optional[float] = None, 
        trigger_price: Optional[float] = None
    ) -> Dict[str, Any]:
        if not self._connected:
            raise ConnectionError("Mock broker is not connected.")

        order_id = f"MOCK_ORD_{uuid.uuid4().hex[:10].upper()}"
        quote = await self.get_quote(symbol)
        avg_price = price if price and order_type != "MARKET" else quote["last_price"]
        
        # Apply standard slippage for market orders (0.05% to 0.1%)
        if order_type == "MARKET":
            slippage = avg_price * random.uniform(0.0005, 0.001)
            if side.upper() == "BUY":
                avg_price = round(avg_price + slippage, 2)
            else:
                avg_price = round(avg_price - slippage, 2)

        order_record = {
            "order_id": order_id,
            "symbol": symbol,
            "exchange": "NSE",
            "side": side.upper(),
            "order_type": order_type.upper(),
            "quantity": quantity,
            "price": price,
            "trigger_price": trigger_price,
            "status": "FILLED",  # Auto-fill immediately in simple mock
            "filled_quantity": quantity,
            "average_price": avg_price,
            "order_timestamp": datetime.utcnow().isoformat(),
            "status_message": "Order executed successfully via mock broker"
        }
        
        self._orders[order_id] = order_record

        # Update mock positions
        self._update_position(symbol, side.upper(), quantity, avg_price)

        return order_record

    def _update_position(self, symbol: str, side: str, quantity: int, price: float):
        current_pos = self._positions.get(symbol, {
            "symbol": symbol,
            "quantity": 0,
            "average_price": 0.0,
            "realized_pnl": 0.0
        })

        qty_change = quantity if side == "BUY" else -quantity
        old_qty = current_pos["quantity"]
        new_qty = old_qty + qty_change

        if new_qty == 0:
            # Position closed
            if old_qty > 0: # Long closed
                pnl = (price - current_pos["average_price"]) * quantity
            else: # Short closed
                pnl = (current_pos["average_price"] - price) * quantity
            current_pos["realized_pnl"] += pnl
            current_pos["quantity"] = 0
            current_pos["average_price"] = 0.0
        else:
            # Position opened or scaled
            if old_qty == 0:
                current_pos["average_price"] = price
            elif (old_qty > 0 and qty_change > 0) or (old_qty < 0 and qty_change < 0):
                # Adding to position: recalculate average price
                total_cost = (current_pos["average_price"] * abs(old_qty)) + (price * quantity)
                current_pos["average_price"] = round(total_cost / abs(new_qty), 2)
            else:
                # Reducing position: realize some P&L but keep average price
                closed_qty = min(abs(old_qty), quantity)
                if old_qty > 0:
                    pnl = (price - current_pos["average_price"]) * closed_qty
                else:
                    pnl = (current_pos["average_price"] - price) * closed_qty
                current_pos["realized_pnl"] += pnl
            
            current_pos["quantity"] = new_qty
            
        self._positions[symbol] = current_pos

    async def cancel_order(self, order_id: str) -> bool:
        if order_id in self._orders:
            order = self._orders[order_id]
            if order["status"] in ["PENDING", "OPEN"]:
                order["status"] = "CANCELLED"
                return True
        return False

    async def get_positions(self) -> List[Dict[str, Any]]:
        # Return positions that have non-zero quantity
        return [pos for pos in self._positions.values() if pos["quantity"] != 0]

    async def get_orders(self) -> List[Dict[str, Any]]:
        return list(self._orders.values())

    async def get_historical_data(
        self, 
        symbol: str, 
        interval: str, 
        from_date: str, 
        to_date: str
    ) -> List[Dict[str, Any]]:
        # Generate simulated candles between dates
        fmt = "%Y-%m-%d"
        try:
            start_dt = datetime.strptime(from_date, fmt)
            end_dt = datetime.strptime(to_date, fmt)
        except ValueError:
            # Fallback to datetime format
            fmt_dt = "%Y-%m-%dT%H:%M:%S"
            start_dt = datetime.strptime(from_date.split(".")[0], fmt_dt)
            end_dt = datetime.strptime(to_date.split(".")[0], fmt_dt)

        delta = end_dt - start_dt
        # Choose candle duration in minutes based on interval
        candle_mins = 5
        if interval == "1m":
            candle_mins = 1
        elif interval == "15m":
            candle_mins = 15
        elif interval == "1h":
            candle_mins = 60
        elif interval == "1d":
            candle_mins = 1440
            
        step = timedelta(minutes=candle_mins)
        current_time = start_dt
        
        candles = []
        base_price = self._base_prices.get(symbol, 150.0)
        curr_price = base_price
        
        while current_time <= end_dt:
            # Random walk candle generation
            op = curr_price
            high = round(op * (1 + random.uniform(0.001, 0.005)), 2)
            low = round(op * (1 - random.uniform(0.001, 0.005)), 2)
            cl = round(random.uniform(low, high), 2)
            vol = random.randint(500, 10000)
            
            candles.append({
                "timestamp": current_time.isoformat(),
                "open": op,
                "high": high,
                "low": low,
                "close": cl,
                "volume": vol,
                "symbol": symbol
            })
            
            curr_price = cl
            current_time += step
            
            # Max 500 candles to prevent huge payload in mock
            if len(candles) >= 500:
                break
                
        return candles
