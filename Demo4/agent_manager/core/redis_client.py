"""
Redis client module for AgentManager caching and task coordination.

This module provides Redis-based caching capabilities for:
- Task polling optimization
- Workflow status caching
- Result storage
- Real-time notifications
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Union
from datetime import timedelta
import asyncio

import redis.asyncio as aioredis
from redis.exceptions import RedisError

from agent_manager.core.models import TaskStep, TaskStatus

logger = logging.getLogger(__name__)


class RedisClient:
    """Async Redis client for AgentManager caching operations."""
    
    def __init__(self, redis_url: Optional[str] = None):
        """Initialize Redis client.
        
        Args:
            redis_url: Redis connection URL (defaults to environment variable)
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6380")
        self.redis: Optional[aioredis.Redis] = None
        
        # TTL settings from environment
        self.ttl_ready_tasks = int(os.getenv("REDIS_TTL_READY_TASKS", "300"))
        self.ttl_workflow_status = int(os.getenv("REDIS_TTL_WORKFLOW_STATUS", "600"))
        self.ttl_task_results = int(os.getenv("REDIS_TTL_TASK_RESULTS", "3600"))
        
        # Debug logging
        logger.info(f"Redis client initialized with URL: {self.redis_url}")
        
    async def connect(self) -> None:
        """Establish Redis connection."""
        try:
            self.redis = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                retry_on_timeout=True,
                socket_connect_timeout=10,
                socket_timeout=10
            )
            
            # Test connection
            await self.redis.ping()
            logger.info(f"Connected to Redis at {self.redis_url}")
            
        except RedisError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            logger.info("Disconnected from Redis")
    
    async def is_connected(self) -> bool:
        """Check if Redis is connected and responsive."""
        try:
            if not self.redis:
                return False
            await self.redis.ping()
            return True
        except RedisError:
            return False
    
    # Task Caching Methods
    async def cache_ready_tasks(self, agent_role: str, tasks: List[TaskStep], ttl: Optional[int] = None) -> None:
        """Cache ready tasks for a specific agent role.
        
        Args:
            agent_role: Agent role (analyst, developer, etc.)
            tasks: List of ready tasks
            ttl: Time to live in seconds (defaults to environment setting)
        """
        if not self.redis:
            return
            
        ttl = ttl or self.ttl_ready_tasks
            
        try:
            key = f"ready_tasks:{agent_role}"
            serialized_tasks = [task.model_dump() for task in tasks]
            
            await self.redis.setex(
                key,
                ttl,
                json.dumps(serialized_tasks)
            )
            
            logger.debug(f"Cached {len(tasks)} ready tasks for {agent_role}")
            
        except (RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to cache ready tasks for {agent_role}: {e}")
    
    async def get_cached_ready_tasks(self, agent_role: str) -> Optional[List[TaskStep]]:
        """Get cached ready tasks for an agent role.
        
        Args:
            agent_role: Agent role to get tasks for
            
        Returns:
            List of ready tasks or None if not cached/expired
        """
        if not self.redis:
            return None
            
        try:
            key = f"ready_tasks:{agent_role}"
            cached_data = await self.redis.get(key)
            
            if not cached_data:
                return None
                
            serialized_tasks = json.loads(cached_data)
            return [TaskStep(**task_data) for task_data in serialized_tasks]
            
        except (RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to retrieve cached ready tasks for {agent_role}: {e}")
            return None
    
    async def invalidate_ready_tasks_cache(self, agent_role: Optional[str] = None) -> None:
        """Invalidate ready tasks cache.
        
        Args:
            agent_role: Specific role to invalidate, or None for all roles
        """
        if not self.redis:
            return
            
        try:
            if agent_role:
                key = f"ready_tasks:{agent_role}"
                await self.redis.delete(key)
                logger.debug(f"Invalidated ready tasks cache for {agent_role}")
            else:
                # Invalidate all ready tasks
                pattern = "ready_tasks:*"
                keys = await self.redis.keys(pattern)
                if keys:
                    await self.redis.delete(*keys)
                    logger.debug(f"Invalidated {len(keys)} ready tasks cache entries")
                    
        except RedisError as e:
            logger.warning(f"Failed to invalidate ready tasks cache: {e}")
    
    # Workflow Status Caching
    async def cache_workflow_status(self, workflow_id: str, status_data: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """Cache workflow status.
        
        Args:
            workflow_id: Workflow identifier
            status_data: Complete workflow status data
            ttl: Time to live in seconds (defaults to environment setting)
        """
        if not self.redis:
            return
            
        ttl = ttl or self.ttl_workflow_status
            
        try:
            key = f"workflow_status:{workflow_id}"
            cache_data = {
                **status_data,
                "cached_at": asyncio.get_event_loop().time()
            }
            
            await self.redis.setex(
                key,
                ttl,
                json.dumps(cache_data)
            )
            
            logger.debug(f"Cached workflow status for {workflow_id}")
            
        except (RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to cache workflow status for {workflow_id}: {e}")
    
    async def get_cached_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get cached workflow status.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            Cached workflow status data or None if not cached/expired
        """
        if not self.redis:
            return None
            
        try:
            key = f"workflow_status:{workflow_id}"
            cached_data = await self.redis.get(key)
            
            if not cached_data:
                return None
                
            status_data = json.loads(cached_data)
            # Remove internal cache metadata
            status_data.pop("cached_at", None)
            return status_data
            
        except (RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to retrieve cached workflow status for {workflow_id}: {e}")
            return None
    
    # Task Results Caching
    async def cache_task_result(self, step_id: str, result: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """Cache task execution result.
        
        Args:
            step_id: Task step identifier
            result: Task execution result
            ttl: Time to live in seconds (defaults to environment setting)
        """
        if not self.redis:
            return
            
        ttl = ttl or self.ttl_task_results
            
        try:
            key = f"task_result:{step_id}"
            
            await self.redis.setex(
                key,
                ttl,
                json.dumps(result)
            )
            
            logger.debug(f"Cached result for task {step_id}")
            
        except (RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to cache result for task {step_id}: {e}")
    
    async def get_cached_task_result(self, step_id: str) -> Optional[Dict[str, Any]]:
        """Get cached task result.
        
        Args:
            step_id: Task step identifier
            
        Returns:
            Cached result or None if not cached/expired
        """
        if not self.redis:
            return None
            
        try:
            key = f"task_result:{step_id}"
            cached_data = await self.redis.get(key)
            
            if not cached_data:
                return None
                
            return json.loads(cached_data)
            
        except (RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to retrieve cached result for task {step_id}: {e}")
            return None
    
    # Real-time Notifications
    async def publish_task_update(self, channel: str, message: Dict[str, Any]) -> None:
        """Publish task update notification.
        
        Args:
            channel: Publication channel
            message: Update message
        """
        if not self.redis:
            return
            
        try:
            await self.redis.publish(
                channel,
                json.dumps(message)
            )
            
            logger.debug(f"Published update to channel {channel}")
            
        except (RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to publish to channel {channel}: {e}")
    
    async def subscribe_to_updates(self, channels: List[str]) -> aioredis.client.PubSub:
        """Subscribe to task update channels.
        
        Args:
            channels: List of channels to subscribe to
            
        Returns:
            Redis PubSub object for listening to updates
        """
        if not self.redis:
            raise RuntimeError("Redis not connected")
            
        try:
            pubsub = self.redis.pubsub()
            await pubsub.subscribe(*channels)
            
            logger.debug(f"Subscribed to channels: {channels}")
            return pubsub
            
        except RedisError as e:
            logger.error(f"Failed to subscribe to channels: {e}")
            raise
    
    # Statistics and Monitoring
    async def increment_counter(self, key: str, expire: Optional[int] = None) -> int:
        """Increment a counter in Redis.
        
        Args:
            key: Counter key
            expire: Optional expiration time in seconds
            
        Returns:
            New counter value
        """
        if not self.redis:
            return 0
            
        try:
            count = await self.redis.incr(key)
            
            if expire and count == 1:  # Only set expiration on first increment
                await self.redis.expire(key, expire)
            
            return count
            
        except RedisError as e:
            logger.warning(f"Failed to increment counter {key}: {e}")
            return 0
    
    async def get_counter(self, key: str) -> int:
        """Get counter value.
        
        Args:
            key: Counter key
            
        Returns:
            Counter value or 0 if not found
        """
        if not self.redis:
            return 0
            
        try:
            value = await self.redis.get(key)
            return int(value) if value else 0
            
        except (RedisError, ValueError) as e:
            logger.warning(f"Failed to get counter {key}: {e}")
            return 0
    
    # Cache Management
    async def clear_cache(self, pattern: str = "*") -> int:
        """Clear cache entries matching a pattern.
        
        Args:
            pattern: Redis key pattern (default: all keys)
            
        Returns:
            Number of keys deleted
        """
        if not self.redis:
            return 0
            
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                deleted = await self.redis.delete(*keys)
                logger.info(f"Cleared {deleted} cache entries matching pattern '{pattern}'")
                return deleted
            return 0
            
        except RedisError as e:
            logger.warning(f"Failed to clear cache with pattern '{pattern}': {e}")
            return 0
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get Redis cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        if not self.redis:
            return {"connected": False}
            
        try:
            info = await self.redis.info()
            stats = {
                "connected": True,
                "redis_version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
            }
            
            # Calculate hit ratio
            hits = stats["keyspace_hits"]
            misses = stats["keyspace_misses"]
            total_requests = hits + misses
            
            if total_requests > 0:
                stats["hit_ratio"] = hits / total_requests
            else:
                stats["hit_ratio"] = 0.0
                
            return stats
            
        except RedisError as e:
            logger.warning(f"Failed to get cache stats: {e}")
            return {"connected": False, "error": str(e)}


# Global Redis client instance (initialized lazily)
redis_client: Optional[RedisClient] = None


def get_redis_client_instance() -> RedisClient:
    """Get or create the global Redis client instance."""
    global redis_client
    if redis_client is None:
        redis_client = RedisClient()
    return redis_client


async def get_redis_client() -> RedisClient:
    """Dependency injection function for FastAPI endpoints."""
    client = get_redis_client_instance()
    try:
        if not await client.is_connected():
            await client.connect()
    except Exception as e:
        logger.warning(f"Redis dependency injection failed: {e}")
        # Return the client anyway, but it won't be connected
        # All methods in RedisClient check for connection and gracefully degrade
    return client


async def startup_redis():
    """Initialize Redis client on application startup."""
    try:
        client = get_redis_client_instance()
        await client.connect()
    except Exception as e:
        logger.warning(f"Redis startup failed, continuing without cache: {e}")


async def shutdown_redis():
    """Cleanup Redis client on application shutdown."""
    client = get_redis_client_instance()
    await client.disconnect()