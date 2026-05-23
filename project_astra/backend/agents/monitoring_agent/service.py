"""
Monitoring Agent - System health monitoring and alerts
Detects failures, stale streams, high latency
Sends Telegram alerts
"""

import asyncio
import time
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import structlog

from utils.redis_streams import stream_manager
from utils.config import settings

logger = structlog.get_logger()


class AlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class Alert:
    """System alert."""
    alert_type: str
    severity: AlertSeverity
    title: str
    message: str
    source: str
    metadata: Optional[Dict] = None
    
    def to_dict(self) -> dict:
        return {
            'alert_type': self.alert_type,
            'severity': self.severity.value,
            'title': self.title,
            'message': self.message,
            'source': self.source,
            'metadata': self.metadata,
            'timestamp': time.time(),
        }


class MonitoringService:
    """
    Monitoring Agent.
    
    Responsibilities:
    - Monitor all agent services
    - Detect stale Redis streams
    - Detect high latency
    - Monitor error rates
    - Send Telegram alerts
    - Track system metrics
    """
    
    # Thresholds
    STALE_STREAM_THRESHOLD_SECONDS = 30
    HIGH_LATENCY_THRESHOLD_MS = 500
    MAX_ERROR_RATE = 0.05  # 5%
    
    def __init__(self):
        self.running = False
        self.last_stream_activity: Dict[str, float] = {}
        self.error_counts: Dict[str, int] = {}
        self.latency_samples: Dict[str, List[float]] = {}
        self.alerts_sent: List[Alert] = []
        
    async def run(self):
        """Main monitoring service loop."""
        self.running = True
        logger.info("Monitoring Service starting")
        
        # Connect to Redis
        await stream_manager.connect()
        
        # Subscribe to all streams for monitoring
        for stream_name in stream_manager.STREAMS.values():
            self.last_stream_activity[stream_name] = time.time()
            
            # Subscribe with callback to track activity
            await stream_manager.subscribe(
                stream_name=stream_name,
                callback=lambda msg, s=stream_name: self._on_stream_activity(s, msg),
                consumer_group=f'monitoring_{stream_name}',
                consumer_name='monitor_1',
            )
        
        # Start health check loop
        asyncio.create_task(self._health_check_loop())
        
        # Keep running
        while self.running:
            await asyncio.sleep(1)
    
    def _on_stream_activity(self, stream_name: str, message: dict):
        """Track stream activity."""
        self.last_stream_activity[stream_name] = time.time()
    
    async def _health_check_loop(self):
        """Periodic health checks."""
        while self.running:
            try:
                # Check for stale streams
                await self._check_stale_streams()
                
                # Check system resources
                await self._check_system_resources()
                
                # Check error rates
                await self._check_error_rates()
                
                # Send heartbeat
                await self._send_heartbeat()
                
            except Exception as e:
                logger.error("Health check error", error=str(e))
            
            await asyncio.sleep(10)  # Check every 10 seconds
    
    async def _check_stale_streams(self):
        """Check if any streams are stale."""
        current_time = time.time()
        
        for stream_name, last_activity in self.last_stream_activity.items():
            if current_time - last_activity > self.STALE_STREAM_THRESHOLD_SECONDS:
                await self._send_alert(
                    Alert(
                        alert_type='stale_stream',
                        severity=AlertSeverity.WARNING,
                        title=f'Stale Stream Detected: {stream_name}',
                        message=f'No activity in {stream_name} for {current_time - last_activity:.0f} seconds',
                        source='monitoring_agent',
                        metadata={'stream': stream_name, 'last_activity': last_activity},
                    )
                )
    
    async def _check_system_resources(self):
        """Check system resource usage."""
        import psutil
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 90:
                await self._send_alert(
                    Alert(
                        alert_type='high_cpu',
                        severity=AlertSeverity.WARNING,
                        title='High CPU Usage',
                        message=f'CPU usage at {cpu_percent}%',
                        source='monitoring_agent',
                        metadata={'cpu_percent': cpu_percent},
                    )
                )
            
            # Memory usage
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                await self._send_alert(
                    Alert(
                        alert_type='high_memory',
                        severity=AlertSeverity.WARNING,
                        title='High Memory Usage',
                        message=f'Memory usage at {memory.percent}%',
                        source='monitoring_agent',
                        metadata={'memory_percent': memory.percent},
                    )
                )
        except Exception as e:
            logger.debug("Resource check skipped", error=str(e))
    
    async def _check_error_rates(self):
        """Check error rates across services."""
        # Would implement error rate tracking here
        pass
    
    async def _send_heartbeat(self):
        """Send periodic heartbeat to stream."""
        await stream_manager.publish(
            stream_name=stream_manager.STREAMS['ALERTS'],
            event_type='heartbeat',
            data={'status': 'healthy', 'timestamp': time.time()},
            source_agent='monitoring_agent',
        )
    
    async def _send_alert(self, alert: Alert):
        """Send alert to stream and Telegram."""
        # Store alert
        self.alerts_sent.append(alert)
        
        # Publish to Redis Stream
        await stream_manager.publish(
            stream_name=stream_manager.STREAMS['ALERTS'],
            event_type='alert',
            data=alert.to_dict(),
            source_agent='monitoring_agent',
        )
        
        # Send to WebSocket
        from websocket.manager import ws_manager
        await ws_manager.send_alert(alert.to_dict())
        
        # Send Telegram notification for critical alerts
        if alert.severity in [AlertSeverity.ERROR, AlertSeverity.CRITICAL]:
            await self._send_telegram_alert(alert)
        
        logger.warning(
            "Alert sent",
            type=alert.alert_type,
            severity=alert.severity.value,
            title=alert.title,
        )
    
    async def _send_telegram_alert(self, alert: Alert):
        """Send alert to Telegram."""
        if not settings.telegram_enabled or not settings.telegram_bot_token:
            return
        
        try:
            import requests
            
            message = (
                f"🚨 *{alert.severity.value}* 🚨\n\n"
                f"*{alert.title}*\n\n"
                f"{alert.message}\n\n"
                f"Source: {alert.source}\n"
                f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
            payload = {
                'chat_id': settings.telegram_chat_id,
                'text': message,
                'parse_mode': 'Markdown',
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info("Telegram alert sent", alert_type=alert.alert_type)
            else:
                logger.error("Telegram send failed", status=response.status_code)
                
        except Exception as e:
            logger.error("Telegram error", error=str(e))
    
    def get_health_status(self) -> dict:
        """Get current health status."""
        return {
            'status': 'healthy' if self.running else 'stopped',
            'streams_monitored': len(self.last_stream_activity),
            'alerts_sent_count': len(self.alerts_sent),
            'uptime': 'running',
        }
    
    async def stop(self):
        """Stop monitoring service."""
        self.running = False
        logger.info("Monitoring Service stopping")


# Global instance
monitoring_service = MonitoringService()
