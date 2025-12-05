"""
Redis client aur connection management
Real-time state, caching, aur session management ke liye
"""

import redis.asyncio as redis
from typing import Optional
import json
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Async Redis client with helper methods
    Call state, agent presence, aur caching ke liye
    """
    
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
    
    async def connect(self):
        """Redis se connect karo"""
        try:
            self.redis = await redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                db=settings.REDIS_DB,
                max_connections=50,
            )
            # Connection test karo
            await self.redis.ping()
            logger.info("Redis connected successfully")
        except Exception as e:
            logger.warning(f"Redis connection failed (continuing without Redis): {e}")
            self.redis = None  # Continue without Redis
    
    async def disconnect(self):
        """Redis connection close karo"""
        if self.redis:
            await self.redis.close()
            logger.info("Redis disconnected")
    
    async def set(self, key: str, value: any, expire: int = None):
        """
        Key-value set karo with optional expiry
        
        Args:
            key: Redis key
            value: Value (auto JSON serialize hoga agar dict/list hai)
            expire: Expiry in seconds (optional)
        """
        if not self.redis:
            return  # Skip if Redis not available
            
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        
        await self.redis.set(key, value, ex=expire)
    
    async def get(self, key: str, as_json: bool = False):
        """
        Key se value get karo
        
        Args:
            key: Redis key
            as_json: Agar True hai toh JSON parse karega
        """
        value = await self.redis.get(key)
        
        if value and as_json:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        
        return value
    
    async def delete(self, key: str):
        """Key ko delete karo"""
        await self.redis.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Check karo key exist karti hai ya nahi"""
        return await self.redis.exists(key) > 0
    
    async def expire(self, key: str, seconds: int):
        """Key par expiry set karo"""
        await self.redis.expire(key, seconds)
    
    # Agent Presence Methods
    
    async def set_agent_online(self, agent_id: int):
        """Agent ko online mark karo"""
        await self.set(f"agent:online:{agent_id}", "1", expire=300)  # 5 min TTL
    
    async def set_agent_offline(self, agent_id: int):
        """Agent ko offline mark karo"""
        await self.delete(f"agent:online:{agent_id}")
    
    async def is_agent_online(self, agent_id: int) -> bool:
        """Check karo agent online hai ya nahi"""
        return await self.exists(f"agent:online:{agent_id}")
    
    # Call State Methods
    
    async def set_call_state(self, call_id: str, state: dict, expire: int = 3600):
        """
        Call ki current state save karo
        
        Args:
            call_id: Unique call ID
            state: Call state dict (status, agent_id, customer_id, etc.)
            expire: State expiry (default 1 hour)
        """
        await self.set(f"call:state:{call_id}", state, expire=expire)
    
    async def get_call_state(self, call_id: str) -> Optional[dict]:
        """Call ki state get karo"""
        return await self.get(f"call:state:{call_id}", as_json=True)
    
    async def delete_call_state(self, call_id: str):
        """Call state delete karo (call end hone par)"""
        await self.delete(f"call:state:{call_id}")
    
    async def set_active_call(self, agent_id: int, call_id: str):
        """Agent ke active call ko track karo"""
        await self.set(f"agent:active_call:{agent_id}", call_id, expire=7200)
    
    async def get_active_call(self, agent_id: int) -> Optional[str]:
        """Agent ki active call ID get karo"""
        return await self.get(f"agent:active_call:{agent_id}")
    
    async def remove_active_call(self, agent_id: int):
        """Agent ki active call remove karo"""
        await self.delete(f"agent:active_call:{agent_id}")
    
    # Session Management
    
    async def save_session(self, session_id: str, data: dict, expire: int = 3600):
        """User session save karo"""
        await self.set(f"session:{session_id}", data, expire=expire)
    
    async def get_session(self, session_id: str) -> Optional[dict]:
        """Session data get karo"""
        return await self.get(f"session:{session_id}", as_json=True)
    
    async def delete_session(self, session_id: str):
        """Session delete karo (logout par)"""
        await self.delete(f"session:{session_id}")
    
    # Pub/Sub for real-time events
    
    async def publish(self, channel: str, message: dict):
        """
        Channel par message publish karo
        Real-time events ke liye
        """
        await self.redis.publish(channel, json.dumps(message))
    
    async def subscribe(self, channel: str):
        """Channel ko subscribe karo"""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(channel)
        return pubsub


# Global Redis client instance
redis_client = RedisClient()


async def get_redis() -> RedisClient:
    """
    Redis client dependency
    FastAPI routes me use karne ke liye
    """
    return redis_client
