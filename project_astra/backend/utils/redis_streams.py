"""
Redis Stream Manager for Inter-Agent Communication
Handles publishing and subscribing to Redis Streams
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
import redis.asyncio as aioredis
import structlog

from utils.config import settings

logger = structlog.get_logger()


@dataclass
class StreamMessage:
    """Base message structure for Redis Streams."""
    stream_name: str
    event_type: str
    timestamp: float
    data: Dict[str, Any]
    source_agent: str
    message_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class RedisStreamManager:
    """
    Manages Redis Streams for inter-agent communication.
    
    Streams:
    - market_ticks: Raw tick data from broker
    - candles_1m: 1-minute candle updates
    - candles_5m: 5-minute candle updates
    - features_stream: Calculated features
    - regime_stream: Regime detection updates
    - strategy_signals: Strategy-generated signals
    - risk_approved_signals: Risk-approved trade candidates
    - execution_orders: Orders sent to execution
    - execution_updates: Order status updates
    - alerts_stream: System alerts and notifications
    """
    
    # Define all stream names
    STREAMS = {
        'MARKET_TICKS': 'market_ticks',
        'CANDLES_1M': 'candles_1m',
        'CANDLES_5M': 'candles_5m',
        'FEATURES': 'features_stream',
        'REGIME': 'regime_stream',
        'STRATEGY_SIGNALS': 'strategy_signals',
        'RISK_APPROVED': 'risk_approved_signals',
        'EXECUTION_ORDERS': 'execution_orders',
        'EXECUTION_UPDATES': 'execution_updates',
        'ALERTS': 'alerts_stream',
    }
    
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self.running = False
        self.consumers: Dict[str, List[Callable]] = {}
        self.consumer_tasks: Dict[str, asyncio.Task] = {}
        
    async def connect(self):
        """Establish connection to Redis."""
        try:
            self.redis = await aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            logger.info("Connected to Redis", url=settings.redis_url)
            
            # Create streams if they don't exist
            await self._initialize_streams()
            
        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            raise
    
    async def disconnect(self):
        """Close Redis connection."""
        self.running = False
        
        # Cancel all consumer tasks
        for task in self.consumer_tasks.values():
            task.cancel()
        
        if self.consumer_tasks:
            await asyncio.gather(*self.consumer_tasks.values(), return_exceptions=True)
        
        if self.redis:
            await self.redis.close()
            logger.info("Disconnected from Redis")
    
    async def _initialize_streams(self):
        """Initialize all required streams."""
        for stream_name in self.STREAMS.values():
            try:
                # Create stream with a dummy entry, then trim it
                await self.redis.xadd(stream_name, {"init": "true"}, maxlen=1)
                await self.redis.xtrim(stream_name, maxlen=0)
                logger.debug(f"Initialized stream: {stream_name}")
            except Exception as e:
                logger.warning(f"Stream initialization warning", stream=stream_name, error=str(e))
    
    async def publish(self, stream_name: str, event_type: str, data: Dict[str, Any], source_agent: str) -> str:
        """
        Publish a message to a Redis Stream.
        
        Args:
            stream_name: Name of the stream
            event_type: Type of event
            data: Event data payload
            source_agent: Name of the publishing agent
            
        Returns:
            Message ID
        """
        if not self.redis:
            raise RuntimeError("Redis not connected")
        
        message = StreamMessage(
            stream_name=stream_name,
            event_type=event_type,
            timestamp=time.time(),
            data=data,
            source_agent=source_agent,
        )
        
        try:
            message_id = await self.redis.xadd(
                stream_name,
                {"message": message.to_json()},
                maxlen=10000,  # Keep last 10k messages per stream
            )
            logger.debug(
                "Published to stream",
                stream=stream_name,
                event_type=event_type,
                message_id=message_id,
            )
            return message_id
        except Exception as e:
            logger.error("Failed to publish to stream", stream=stream_name, error=str(e))
            raise
    
    async def subscribe(
        self,
        stream_name: str,
        callback: Callable[[Dict[str, Any]], Any],
        consumer_group: Optional[str] = None,
        consumer_name: Optional[str] = None,
        batch_size: int = 1,
    ):
        """
        Subscribe to a Redis Stream and process messages.
        
        Args:
            stream_name: Name of the stream to subscribe to
            callback: Async callback function to process messages
            consumer_group: Optional consumer group name
            consumer_name: Optional consumer name
            batch_size: Number of messages to read at once
        """
        if not self.redis:
            raise RuntimeError("Redis not connected")
        
        # Setup consumer group if specified
        if consumer_group:
            try:
                await self.redis.xgroup_create(
                    stream_name,
                    consumer_group,
                    id="0",
                    mkstream=True,
                )
                logger.info(f"Created consumer group", stream=stream_name, group=consumer_group)
            except Exception as e:
                if "BUSYGROUP" not in str(e):
                    logger.warning(f"Consumer group creation warning", error=str(e))
        
        async def consume():
            """Consumer loop."""
            while self.running:
                try:
                    if consumer_group and consumer_name:
                        # Read from consumer group
                        messages = await self.redis.xreadgroup(
                            groupname=consumer_group,
                            consumername=consumer_name,
                            streams={stream_name: ">"},
                            count=batch_size,
                            block=5000,  # Block for 5 seconds
                        )
                    else:
                        # Simple read without consumer group
                        messages = await self.redis.xread(
                            streams={stream_name: "$"},
                            count=batch_size,
                            block=5000,
                        )
                    
                    if messages:
                        for stream, msg_list in messages:
                            for msg_id, fields in msg_list:
                                try:
                                    message_data = json.loads(fields.get("message", "{}"))
                                    await callback(message_data)
                                    
                                    # Acknowledge message if using consumer group
                                    if consumer_group:
                                        await self.redis.xack(stream_name, consumer_group, msg_id)
                                        
                                except json.JSONDecodeError as e:
                                    logger.error("Invalid JSON in stream message", error=str(e))
                                except Exception as e:
                                    logger.error("Error processing stream message", error=str(e))
                                    
                except asyncio.CancelledError:
                    logger.info(f"Consumer cancelled for stream: {stream_name}")
                    break
                except Exception as e:
                    logger.error("Stream consumption error", stream=stream_name, error=str(e))
                    await asyncio.sleep(1)  # Back off on error
        
        # Start consumer task
        task = asyncio.create_task(consume())
        self.consumer_tasks[stream_name] = task
        logger.info(f"Started consumer for stream: {stream_name}")
    
    async def get_stream_info(self, stream_name: str) -> Dict[str, Any]:
        """Get information about a stream."""
        if not self.redis:
            raise RuntimeError("Redis not connected")
        
        info = await self.redis.xinfo_stream(stream_name)
        return info
    
    async def get_pending_messages(
        self,
        stream_name: str,
        consumer_group: str,
    ) -> List[Dict[str, Any]]:
        """Get pending (unacknowledged) messages for a consumer group."""
        if not self.redis:
            raise RuntimeError("Redis not connected")
        
        pending = await self.redis.xpending_range(
            stream_name,
            consumer_group,
            min="-",
            max="+",
            count=100,
        )
        return pending
    
    async def replay_stream(
        self,
        stream_name: str,
        start_id: str = "-",
        end_id: str = "+",
        count: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Replay messages from a stream for debugging/backtesting.
        
        Args:
            stream_name: Name of the stream
            start_id: Start message ID (default: beginning)
            end_id: End message ID (default: end)
            count: Maximum number of messages to retrieve
            
        Returns:
            List of messages
        """
        if not self.redis:
            raise RuntimeError("Redis not connected")
        
        messages = await self.redis.xrange(
            stream_name,
            min=start_id,
            max=end_id,
            count=count,
        )
        
        result = []
        for msg_id, fields in messages:
            try:
                message_data = json.loads(fields.get("message", "{}"))
                message_data['message_id'] = msg_id
                result.append(message_data)
            except json.JSONDecodeError:
                continue
        
        return result


# Global instance
stream_manager = RedisStreamManager()
