"""
Execution Agent - Paper Trading Engine
Simulates order execution with realistic slippage, latency, and fills
"""

import asyncio
import uuid
import random
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import structlog

from sqlalchemy import select
from utils.redis_streams import stream_manager
from utils.config import settings

logger = structlog.get_logger()


class OrderStatus(str, Enum):
    CREATED = "CREATED"
    SENT = "SENT"
    ACK = "ACK"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXITED = "EXITED"


@dataclass
class Order:
    """Order representation."""
    order_id: str
    symbol: str
    exchange: str
    side: str  # BUY, SELL
    order_type: str  # LIMIT, MARKET, SL, SL-M
    quantity: int
    price: Optional[float]
    trigger_price: Optional[float]
    product: str  # MIS, CNC, NRML
    status: OrderStatus = OrderStatus.CREATED
    filled_quantity: int = 0
    average_price: float = 0.0
    created_at: float = field(default_factory=lambda: asyncio.get_event_loop().time())
    updated_at: float = field(default_factory=lambda: asyncio.get_event_loop().time())
    
    def to_dict(self) -> dict:
        return {
            'order_id': self.order_id,
            'symbol': self.symbol,
            'exchange': self.exchange,
            'side': self.side,
            'order_type': self.order_type,
            'quantity': self.quantity,
            'price': self.price,
            'trigger_price': self.trigger_price,
            'product': self.product,
            'status': self.status.value,
            'filled_quantity': self.filled_quantity,
            'average_price': self.average_price,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }


@dataclass
class Fill:
    """Order fill/execution."""
    fill_id: str
    order_id: str
    symbol: str
    side: str
    quantity: int
    price: float
    brokerage: float
    stt: float
    exchange_charges: float
    gst: float
    stamp_duty: float
    total_charges: float
    pnl: Optional[float]
    fill_timestamp: float
    
    def to_dict(self) -> dict:
        return {
            'fill_id': self.fill_id,
            'order_id': self.order_id,
            'symbol': self.symbol,
            'side': self.side,
            'quantity': self.quantity,
            'price': self.price,
            'brokerage': self.brokerage,
            'stt': self.stt,
            'exchange_charges': self.exchange_charges,
            'gst': self.gst,
            'stamp_duty': self.stamp_duty,
            'total_charges': self.total_charges,
            'pnl': self.pnl,
            'fill_timestamp': self.fill_timestamp,
        }


class ExecutionService:
    """
    Execution Agent - Paper Trading Engine.
    
    Simulates:
    - Order placement
    - Slippage (0.05% - 0.2%)
    - Latency (100ms - 500ms)
    - Partial fills
    - Order rejection
    - Stop loss and target exits
    - Trailing stops
    
    State Machine:
    CREATED → SENT → ACK → PARTIAL → FILLED → EXITED
    """
    
    # Simulation parameters
    MIN_LATENCY_MS = 100
    MAX_LATENCY_MS = 500
    MIN_SLIPPAGE_PCT = 0.0005  # 0.05%
    MAX_SLIPPAGE_PCT = 0.002   # 0.2%
    PARTIAL_FILL_PROBABILITY = 0.1  # 10% chance of partial fill
    REJECTION_PROBABILITY = 0.02    # 2% chance of rejection
    
    # Indian brokerage charges (approximate)
    BROKERAGE_PER_ORDER = 20.0  # Rs 20 per order
    STT_BUY = 0.0003   # 0.03% on buy
    STT_SELL = 0.0006  # 0.06% on sell
    EXCHANGE_CHARGES = 0.0000323  # NSE charges
    GST_RATE = 0.18    # 18%
    STAMP_DUTY_BUY = 0.00015  # 0.015%
    
    def __init__(self):
        self.running = False
        self.orders: Dict[str, Order] = {}
        self.positions: Dict[str, dict] = {}  # symbol -> position info
        self.pending_orders: List[Order] = []
        
    async def run(self):
        """Main execution service loop."""
        self.running = True
        logger.info("Execution Service starting (PAPER TRADING MODE)")
        
        # Connect to Redis
        await stream_manager.connect()
        
        # Subscribe to risk-approved signals
        await stream_manager.subscribe(
            stream_name=stream_manager.STREAMS['RISK_APPROVED'],
            callback=self._on_trade_approved,
            consumer_group='execution_agent',
            consumer_name='order_executor_1',
        )
        
        # Process pending orders
        asyncio.create_task(self._process_pending_orders())
        
        # Keep running
        while self.running:
            await asyncio.sleep(1)
    
    async def _on_trade_approved(self, message: dict):
        """Process risk-approved trade."""
        try:
            trade_data = message.get('data', {})
            
            # Create order from approved trade
            order = await self._create_order(trade_data)
            
            if order:
                # Add to pending orders
                self.pending_orders.append(order)
                self.orders[order.order_id] = order
                
                logger.info(
                    "Order created",
                    order_id=order.order_id,
                    symbol=order.symbol,
                    side=order.side,
                    quantity=order.quantity,
                )
                
        except Exception as e:
            logger.error("Error processing approved trade", error=str(e))
    
    async def _create_order(self, trade_data: dict) -> Optional[Order]:
        """Create order from trade data."""
        symbol = trade_data.get('symbol', '')
        entry_price = trade_data.get('entry_price', 0.0)
        quantity = trade_data.get('approved_quantity', 0)
        signal_id = trade_data.get('signal_id', 0)
        
        if not symbol or quantity <= 0:
            return None
        
        # Determine side based on strategy signal direction from DB
        side = 'BUY'
        try:
            from database.connection import async_session_factory
            from database.models import StrategySignal
            async with async_session_factory() as session:
                stmt = select(StrategySignal).where(StrategySignal.id == signal_id)
                res = await session.execute(stmt)
                sig = res.scalar_one_or_none()
                if sig and sig.direction:
                    side = 'BUY' if sig.direction == 'LONG' else 'SELL'
        except Exception as e:
            logger.error("Failed to query signal direction for order creation", signal_id=signal_id, error=str(e))
        
        order = Order(
            order_id=f"ORD_{uuid.uuid4().hex[:12]}",
            symbol=symbol,
            exchange='NSE',
            side=side,
            order_type='MARKET',
            quantity=quantity,
            price=entry_price,
            trigger_price=None,
            product='MIS',
            status=OrderStatus.CREATED,
        )
        
        # Save order to database
        await self._save_order_to_db(order, signal_id)
        
        return order
    
    async def _process_pending_orders(self):
        """Process pending orders with simulated latency."""
        while self.running:
            if self.pending_orders:
                order = self.pending_orders[0]
                
                # Simulate latency
                latency_ms = random.randint(self.MIN_LATENCY_MS, self.MAX_LATENCY_MS)
                await asyncio.sleep(latency_ms / 1000.0)
                
                # Check for rejection
                if random.random() < self.REJECTION_PROBABILITY:
                    order.status = OrderStatus.REJECTED
                    order.updated_at = asyncio.get_event_loop().time()
                    
                    await self._publish_order_update(order)
                    self.pending_orders.remove(order)
                    
                    logger.warning("Order rejected", order_id=order.order_id)
                    continue
                
                # Send order
                order.status = OrderStatus.SENT
                order.updated_at = asyncio.get_event_loop().time()
                await self._publish_order_update(order)
                
                # Simulate acknowledgment
                await asyncio.sleep(0.1)
                order.status = OrderStatus.ACK
                order.updated_at = asyncio.get_event_loop().time()
                await self._publish_order_update(order)
                
                # Execute fill
                await self._execute_fill(order)
                
                self.pending_orders.remove(order)
            else:
                await asyncio.sleep(0.5)
    
    async def _execute_fill(self, order: Order):
        """Execute order fill with simulated slippage."""
        # Get current market price (mock)
        current_price = order.price or 100.0
        
        # Apply slippage
        slippage_pct = random.uniform(self.MIN_SLIPPAGE_PCT, self.MAX_SLIPPAGE_PCT)
        if order.side == 'BUY':
            fill_price = current_price * (1 + slippage_pct)
        else:
            fill_price = current_price * (1 - slippage_pct)
        
        # Check for partial fill
        if random.random() < self.PARTIAL_FILL_PROBABILITY:
            fill_qty = int(order.quantity * random.uniform(0.5, 0.9))
            remaining_qty = order.quantity - fill_qty
            
            # First partial fill
            await self._create_fill(order, fill_qty, fill_price)
            order.filled_quantity += fill_qty
            order.status = OrderStatus.PARTIAL
            order.updated_at = asyncio.get_event_loop().time()
            await self._publish_order_update(order)
            
            # Second fill for remaining
            await asyncio.sleep(0.2)
            await self._create_fill(order, remaining_qty, fill_price)
            order.filled_quantity = order.quantity
            order.status = OrderStatus.FILLED
            order.average_price = fill_price
            order.updated_at = asyncio.get_event_loop().time()
            await self._publish_order_update(order)
            
            # Update position (partial fill complete)
            await self._update_position(order, fill_price)
        else:
            # Full fill
            await self._create_fill(order, order.quantity, fill_price)
            order.filled_quantity = order.quantity
            order.status = OrderStatus.FILLED
            order.average_price = fill_price
            order.updated_at = asyncio.get_event_loop().time()
            await self._publish_order_update(order)
            
            # Update position
            await self._update_position(order, fill_price)
    
    async def _create_fill(self, order: Order, quantity: int, price: float):
        """Create fill record with charges calculation."""
        fill_value = quantity * price
        
        # Calculate charges
        brokerage = self.BROKERAGE_PER_ORDER
        stt = fill_value * (self.STT_SELL if order.side == 'SELL' else self.STT_BUY)
        exchange_charges = fill_value * self.EXCHANGE_CHARGES
        gst = (brokerage + exchange_charges) * self.GST_RATE
        stamp_duty = fill_value * self.STAMP_DUTY_BUY if order.side == 'BUY' else 0
        total_charges = brokerage + stt + exchange_charges + gst + stamp_duty
        
        # Calculate PnL (for exit fills)
        pnl = None
        if order.side == 'SELL':
            position = self.positions.get(order.symbol)
            if position:
                pnl = (position['avg_price'] - price) * quantity - total_charges
        
        fill = Fill(
            fill_id=f"FILL_{uuid.uuid4().hex[:12]}",
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=quantity,
            price=price,
            brokerage=brokerage,
            stt=stt,
            exchange_charges=exchange_charges,
            gst=gst,
            stamp_duty=stamp_duty,
            total_charges=total_charges,
            pnl=pnl,
            fill_timestamp=asyncio.get_event_loop().time(),
        )
        
        # Save fill to database
        await self._save_fill_to_db(fill)

        # Publish fill
        await stream_manager.publish(
            stream_name=stream_manager.STREAMS['EXECUTION_UPDATES'],
            event_type='fill',
            data=fill.to_dict(),
            source_agent='execution_agent',
        )
        
        logger.info(
            "Order filled",
            order_id=order.order_id,
            quantity=quantity,
            price=price,
            charges=total_charges,
        )
    
    async def _update_position(self, order: Order, fill_price: float):
        """Update position after fill."""
        symbol = order.symbol
        
        if order.side == 'BUY':
            # New or add to position
            if symbol in self.positions:
                pos = self.positions[symbol]
                total_qty = pos['quantity'] + order.quantity
                avg_price = ((pos['quantity'] * pos['avg_price']) + 
                           (order.quantity * fill_price)) / total_qty
                pos['quantity'] = total_qty
                pos['avg_price'] = avg_price
            else:
                self.positions[symbol] = {
                    'quantity': order.quantity,
                    'avg_price': fill_price,
                    'side': 'LONG',
                    'entry_time': asyncio.get_event_loop().time(),
                }
        else:
            # Reduce or close position
            if symbol in self.positions:
                pos = self.positions[symbol]
                pos['quantity'] -= order.quantity
                if pos['quantity'] <= 0:
                    del self.positions[symbol]
                    
        # Persist position to database
        p_qty = self.positions[symbol]['quantity'] if symbol in self.positions else 0
        p_avg = self.positions[symbol]['avg_price'] if symbol in self.positions else 0.0
        p_side = self.positions[symbol]['side'] if symbol in self.positions else 'LONG'
        await self._save_position_to_db(symbol, p_qty, p_avg, p_side)
    
    async def _publish_order_update(self, order: Order):
        """Publish order status update."""
        # Update order status in database
        await self._update_order_status_in_db(order)

        await stream_manager.publish(
            stream_name=stream_manager.STREAMS['EXECUTION_UPDATES'],
            event_type='order_update',
            data=order.to_dict(),
            source_agent='execution_agent',
        )
        
        # Also send to WebSocket
        from websocket.manager import ws_manager
        await ws_manager.send_order_update(order.to_dict())

    async def _save_order_to_db(self, order: Order, signal_id: int):
        try:
            from database.connection import async_session_factory
            from database.models import Order as DbOrder, TradeCandidate
            
            async with async_session_factory() as session:
                # Get candidate_id
                stmt = select(TradeCandidate).where(TradeCandidate.signal_id == signal_id)
                res = await session.execute(stmt)
                cand = res.scalar_one_or_none()
                candidate_id = cand.id if cand else None
                
                db_order = DbOrder(
                    order_id=order.order_id,
                    candidate_id=candidate_id,
                    symbol=order.symbol,
                    exchange=order.exchange,
                    side=order.side,
                    order_type=order.order_type,
                    quantity=order.quantity,
                    price=float(order.price) if order.price else None,
                    status=order.status.value,
                    filled_quantity=order.filled_quantity,
                    average_price=float(order.average_price) if order.average_price else None,
                    placed_at=datetime.utcnow()
                )
                session.add(db_order)
                await session.commit()
        except Exception as e:
            logger.error("Failed to save order to database", order_id=order.order_id, error=str(e))

    async def _update_order_status_in_db(self, order: Order):
        try:
            from database.connection import async_session_factory
            from database.models import Order as DbOrder
            
            async with async_session_factory() as session:
                stmt = select(DbOrder).where(DbOrder.order_id == order.order_id)
                res = await session.execute(stmt)
                db_order = res.scalar_one_or_none()
                
                if db_order:
                    db_order.status = order.status.value
                    db_order.filled_quantity = order.filled_quantity
                    db_order.average_price = float(order.average_price) if order.average_price else None
                    await session.commit()
        except Exception as e:
            logger.error("Failed to update order status in database", order_id=order.order_id, error=str(e))

    async def _save_fill_to_db(self, fill_obj: Fill):
        try:
            from database.connection import async_session_factory
            from database.models import Fill as DbFill, Order as DbOrder
            
            async with async_session_factory() as session:
                stmt = select(DbOrder).where(DbOrder.order_id == fill_obj.order_id)
                res = await session.execute(stmt)
                db_order = res.scalar_one_or_none()
                order_db_id = db_order.id if db_order else None
                
                db_fill = DbFill(
                    order_id=order_db_id,
                    fill_id=fill_obj.fill_id,
                    symbol=fill_obj.symbol,
                    side=fill_obj.side,
                    quantity=fill_obj.quantity,
                    price=float(fill_obj.price),
                    brokerage=float(fill_obj.brokerage),
                    stt=float(fill_obj.stt),
                    exchange_charges=float(fill_obj.exchange_charges),
                    gst=float(fill_obj.gst),
                    stamp_duty=float(fill_obj.stamp_duty),
                    total_charges=float(fill_obj.total_charges),
                    pnl=float(fill_obj.pnl) if fill_obj.pnl else None,
                    fill_timestamp=datetime.utcnow()
                )
                session.add(db_fill)
                await session.commit()
        except Exception as e:
            logger.error("Failed to save fill to database", fill_id=fill_obj.fill_id, error=str(e))

    async def _save_position_to_db(self, symbol: str, quantity: int, average_price: float, side: str):
        try:
            from database.connection import async_session_factory
            from database.models import Position as DbPosition
            
            async with async_session_factory() as session:
                stmt = select(DbPosition).where(DbPosition.symbol == symbol, DbPosition.status == 'OPEN')
                res = await session.execute(stmt)
                pos = res.scalar_one_or_none()
                
                if pos:
                    if quantity <= 0:
                        pos.quantity = 0
                        pos.status = 'CLOSED'
                        pos.exit_time = datetime.utcnow()
                    else:
                        pos.quantity = quantity
                        pos.average_price = float(average_price)
                        pos.current_price = float(average_price)
                else:
                    if quantity > 0:
                        new_pos = DbPosition(
                            symbol=symbol,
                            exchange='NSE',
                            side=side,
                            quantity=quantity,
                            average_price=float(average_price),
                            current_price=float(average_price),
                            unrealized_pnl=0.0,
                            realized_pnl=0.0,
                            entry_time=datetime.utcnow(),
                            status='OPEN'
                        )
                        session.add(new_pos)
                
                await session.commit()
        except Exception as e:
            logger.error("Failed to save position to database", symbol=symbol, error=str(e))

    async def stop(self):
        """Stop execution service."""
        self.running = False
        logger.info("Execution Service stopping")


# Global instance
execution_service = ExecutionService()
