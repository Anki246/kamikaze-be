#!/usr/bin/env python3
"""
Redis Event Bus Infrastructure for 24/7 Trading System
Handles all pub/sub messaging for event-driven architecture
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum

import aioredis
from aioredis import Redis


class EventType(str, Enum):
    """Event types for the trading system."""
    # Market Data Events
    MARKET_DATA_UPDATE = "market_data_update"
    PRICE_CHANGE = "price_change"
    VOLUME_SPIKE = "volume_spike"
    
    # Trading Signal Events
    TRADING_SIGNAL = "trading_signal"
    SIGNAL_CONFIRMED = "signal_confirmed"
    SIGNAL_CANCELLED = "signal_cancelled"
    
    # Order Events
    ORDER_CREATED = "order_created"
    ORDER_FILLED = "order_filled"
    ORDER_CANCELLED = "order_cancelled"
    ORDER_FAILED = "order_failed"
    
    # Portfolio Events
    BALANCE_UPDATE = "balance_update"
    POSITION_UPDATE = "position_update"
    PNL_UPDATE = "pnl_update"
    
    # System Events
    AGENT_STARTED = "agent_started"
    AGENT_STOPPED = "agent_stopped"
    AGENT_ERROR = "agent_error"
    HEALTH_CHECK = "health_check"
    ALERT = "alert"


@dataclass
class BaseEvent:
    """Base event structure."""
    event_type: EventType
    timestamp: datetime
    source: str
    data: Dict[str, Any]
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "data": self.data,
            "correlation_id": self.correlation_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseEvent':
        """Create event from dictionary."""
        return cls(
            event_type=EventType(data["event_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            source=data["source"],
            data=data["data"],
            correlation_id=data.get("correlation_id")
        )


@dataclass
class MarketDataEvent(BaseEvent):
    """Market data event."""
    symbol: str
    price: float
    volume: float
    change_24h: float
    
    def __post_init__(self):
        self.event_type = EventType.MARKET_DATA_UPDATE
        self.data.update({
            "symbol": self.symbol,
            "price": self.price,
            "volume": self.volume,
            "change_24h": self.change_24h
        })


@dataclass
class TradingSignalEvent(BaseEvent):
    """Trading signal event."""
    symbol: str
    signal_type: str  # "BUY", "SELL"
    confidence: float
    strategy: str
    price: float
    
    def __post_init__(self):
        self.event_type = EventType.TRADING_SIGNAL
        self.data.update({
            "symbol": self.symbol,
            "signal_type": self.signal_type,
            "confidence": self.confidence,
            "strategy": self.strategy,
            "price": self.price
        })


@dataclass
class OrderEvent(BaseEvent):
    """Order event."""
    order_id: str
    symbol: str
    side: str
    quantity: float
    price: float
    status: str
    
    def __post_init__(self):
        self.data.update({
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "price": self.price,
            "status": self.status
        })


class EventBus:
    """
    Redis-based event bus for 24/7 trading system.
    
    Features:
    - Pub/Sub messaging
    - Event persistence
    - Dead letter queues
    - Health monitoring
    - Automatic reconnection
    """
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis: Optional[Redis] = None
        self.pubsub = None
        self.subscribers: Dict[str, List[Callable]] = {}
        self.running = False
        self.logger = logging.getLogger("event_bus")
        
        # Channel patterns
        self.CHANNELS = {
            "market_data": "trading:market_data:*",
            "signals": "trading:signals:*",
            "orders": "trading:orders:*",
            "portfolio": "trading:portfolio:*",
            "system": "trading:system:*",
            "alerts": "trading:alerts:*"
        }
    
    async def connect(self) -> bool:
        """Connect to Redis."""
        try:
            self.redis = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            await self.redis.ping()
            self.logger.info("✅ Connected to Redis event bus")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to connect to Redis: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.pubsub:
            await self.pubsub.close()
        if self.redis:
            await self.redis.close()
        self.logger.info("🔌 Disconnected from Redis event bus")
    
    async def publish(self, channel: str, event: BaseEvent) -> bool:
        """Publish an event to a channel."""
        try:
            if not self.redis:
                await self.connect()
            
            # Serialize event
            event_data = json.dumps(event.to_dict())
            
            # Publish to channel
            await self.redis.publish(channel, event_data)
            
            # Store in event log for persistence
            await self._store_event(channel, event)
            
            self.logger.debug(f"📤 Published event {event.event_type} to {channel}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to publish event: {e}")
            return False
    
    async def subscribe(self, pattern: str, callback: Callable[[BaseEvent], None]):
        """Subscribe to events matching a pattern."""
        if pattern not in self.subscribers:
            self.subscribers[pattern] = []
        
        self.subscribers[pattern].append(callback)
        self.logger.info(f"📥 Subscribed to pattern: {pattern}")
    
    async def start_listening(self):
        """Start listening for events."""
        if not self.redis:
            await self.connect()
        
        self.pubsub = self.redis.pubsub()
        
        # Subscribe to all patterns
        for pattern in self.subscribers.keys():
            await self.pubsub.psubscribe(pattern)
        
        self.running = True
        self.logger.info("🎧 Started listening for events")
        
        # Event processing loop
        asyncio.create_task(self._process_events())
    
    async def stop_listening(self):
        """Stop listening for events."""
        self.running = False
        if self.pubsub:
            await self.pubsub.close()
        self.logger.info("🛑 Stopped listening for events")
    
    async def _process_events(self):
        """Process incoming events."""
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "pmessage":
                    pattern = message["pattern"]
                    channel = message["channel"]
                    data = message["data"]
                    
                    try:
                        # Deserialize event
                        event_dict = json.loads(data)
                        event = BaseEvent.from_dict(event_dict)
                        
                        # Call all subscribers for this pattern
                        if pattern in self.subscribers:
                            for callback in self.subscribers[pattern]:
                                try:
                                    await callback(event)
                                except Exception as e:
                                    self.logger.error(f"❌ Error in event callback: {e}")
                    
                    except Exception as e:
                        self.logger.error(f"❌ Error processing event: {e}")
                        
        except Exception as e:
            self.logger.error(f"❌ Error in event processing loop: {e}")
    
    async def _store_event(self, channel: str, event: BaseEvent):
        """Store event for persistence and replay."""
        try:
            # Store in Redis list for event history
            event_key = f"events:{channel}:{event.event_type.value}"
            event_data = json.dumps(event.to_dict())
            
            # Add to list (keep last 1000 events)
            await self.redis.lpush(event_key, event_data)
            await self.redis.ltrim(event_key, 0, 999)
            
            # Set expiration (7 days)
            await self.redis.expire(event_key, 604800)
            
        except Exception as e:
            self.logger.error(f"❌ Failed to store event: {e}")
    
    async def get_event_history(self, channel: str, event_type: EventType, limit: int = 100) -> List[BaseEvent]:
        """Get event history for a channel and event type."""
        try:
            event_key = f"events:{channel}:{event_type.value}"
            events_data = await self.redis.lrange(event_key, 0, limit - 1)
            
            events = []
            for event_data in events_data:
                event_dict = json.loads(event_data)
                events.append(BaseEvent.from_dict(event_dict))
            
            return events
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get event history: {e}")
            return []
    
    async def health_check(self) -> Dict[str, Any]:
        """Check event bus health."""
        try:
            if not self.redis:
                return {"status": "disconnected", "error": "No Redis connection"}
            
            # Test Redis connection
            await self.redis.ping()
            
            # Get connection info
            info = await self.redis.info()
            
            return {
                "status": "healthy",
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "0B"),
                "uptime": info.get("uptime_in_seconds", 0),
                "subscribers": len(self.subscribers)
            }
            
        except Exception as e:
            return {"status": "error", "error": str(e)}


# Global event bus instance
event_bus = EventBus()


# Convenience functions
async def publish_market_data(symbol: str, price: float, volume: float, change_24h: float):
    """Publish market data event."""
    event = MarketDataEvent(
        timestamp=datetime.utcnow(),
        source="market_data_service",
        data={},
        symbol=symbol,
        price=price,
        volume=volume,
        change_24h=change_24h
    )
    await event_bus.publish(f"trading:market_data:{symbol}", event)


async def publish_trading_signal(symbol: str, signal_type: str, confidence: float, strategy: str, price: float):
    """Publish trading signal event."""
    event = TradingSignalEvent(
        timestamp=datetime.utcnow(),
        source="strategy_engine",
        data={},
        symbol=symbol,
        signal_type=signal_type,
        confidence=confidence,
        strategy=strategy,
        price=price
    )
    await event_bus.publish(f"trading:signals:{symbol}", event)


async def publish_order_event(event_type: EventType, order_id: str, symbol: str, side: str, quantity: float, price: float, status: str):
    """Publish order event."""
    event = OrderEvent(
        event_type=event_type,
        timestamp=datetime.utcnow(),
        source="order_manager",
        data={},
        order_id=order_id,
        symbol=symbol,
        side=side,
        quantity=quantity,
        price=price,
        status=status
    )
    await event_bus.publish(f"trading:orders:{symbol}", event)
