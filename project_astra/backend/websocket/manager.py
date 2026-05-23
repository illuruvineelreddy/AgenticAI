"""
WebSocket Manager for real-time frontend updates
"""

import asyncio
import json
from typing import Dict, List, Optional
from fastapi import WebSocket
import structlog

logger = structlog.get_logger()


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        # Store active connections
        self.active_connections: Dict[str, WebSocket] = {}
        # Store subscriptions by topic
        self.subscriptions: Dict[str, List[str]] = {
            'ticks': [],
            'candles': [],
            'signals': [],
            'orders': [],
            'positions': [],
            'alerts': [],
        }
        # Broadcast queue
        self.broadcast_queue: asyncio.Queue = asyncio.Queue()
        
    async def connect(self, websocket: WebSocket, client_id: str = "default"):
        """Accept and store a new WebSocket connection."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client connected", client_id=client_id)
        
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        client_id = None
        for cid, ws in self.active_connections.items():
            if ws == websocket:
                client_id = cid
                break
        
        if client_id:
            del self.active_connections[client_id]
            # Remove from subscriptions
            for topic in self.subscriptions.values():
                if client_id in topic:
                    topic.remove(client_id)
            
            logger.info(f"Client disconnected", client_id=client_id)
    
    async def subscribe(self, client_id: str, topic: str):
        """Subscribe a client to a topic."""
        if topic in self.subscriptions and client_id in self.active_connections:
            if client_id not in self.subscriptions[topic]:
                self.subscriptions[topic].append(client_id)
                logger.info(f"Client subscribed to topic", client_id=client_id, topic=topic)
    
    async def unsubscribe(self, client_id: str, topic: str):
        """Unsubscribe a client from a topic."""
        if topic in self.subscriptions and client_id in self.subscriptions[topic]:
            self.subscriptions[topic].remove(client_id)
            logger.info(f"Client unsubscribed from topic", client_id=client_id, topic=topic)
    
    async def send_personal_message(self, message: dict, client_id: str):
        """Send a message to a specific client."""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message", client_id=client_id, error=str(e))
                self.disconnect(self.active_connections[client_id])
    
    async def broadcast(self, message: dict, topic: Optional[str] = None):
        """
        Broadcast a message to all subscribers.
        
        Args:
            message: Message to broadcast
            topic: If specified, only send to subscribers of this topic
        """
        await self.broadcast_queue.put((message, topic))
    
    async def process_broadcasts(self):
        """Background task to process broadcast queue."""
        while True:
            try:
                message, topic = await self.broadcast_queue.get()
                
                if topic:
                    # Send to topic subscribers
                    for client_id in self.subscriptions.get(topic, []):
                        await self.send_personal_message(message, client_id)
                else:
                    # Send to all connected clients
                    for client_id in self.active_connections.keys():
                        await self.send_personal_message(message, client_id)
                        
            except Exception as e:
                logger.error(f"Broadcast error", error=str(e))
    
    async def send_tick_update(self, symbol: str, data: dict):
        """Send tick update to subscribers."""
        message = {
            'type': 'tick',
            'symbol': symbol,
            'data': data,
            'timestamp': asyncio.get_event_loop().time(),
        }
        await self.broadcast(message, topic='ticks')
    
    async def send_candle_update(self, symbol: str, interval: str, data: dict):
        """Send candle update to subscribers."""
        message = {
            'type': 'candle',
            'symbol': symbol,
            'interval': interval,
            'data': data,
            'timestamp': asyncio.get_event_loop().time(),
        }
        await self.broadcast(message, topic='candles')
    
    async def send_signal(self, strategy: str, signal: dict):
        """Send strategy signal to subscribers."""
        message = {
            'type': 'signal',
            'strategy': strategy,
            'data': signal,
            'timestamp': asyncio.get_event_loop().time(),
        }
        await self.broadcast(message, topic='signals')
    
    async def send_order_update(self, order: dict):
        """Send order status update to subscribers."""
        message = {
            'type': 'order',
            'data': order,
            'timestamp': asyncio.get_event_loop().time(),
        }
        await self.broadcast(message, topic='orders')
    
    async def send_position_update(self, position: dict):
        """Send position update to subscribers."""
        message = {
            'type': 'position',
            'data': position,
            'timestamp': asyncio.get_event_loop().time(),
        }
        await self.broadcast(message, topic='positions')
    
    async def send_alert(self, alert: dict):
        """Send alert to subscribers."""
        message = {
            'type': 'alert',
            'data': alert,
            'timestamp': asyncio.get_event_loop().time(),
        }
        await self.broadcast(message, topic='alerts')


# Global instance
ws_manager = ConnectionManager()
