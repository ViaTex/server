from redis.asyncio import Redis, ConnectionPool
from app.core.config import settings


class RedisClient:
    """Redis client singleton"""
    
    _instance: Redis = None
    _pool: ConnectionPool = None
    
    @classmethod
    async def get_instance(cls) -> Redis:
        """Get Redis instance"""
        if cls._instance is None:
            cls._pool = ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                decode_responses=True,
            )
            cls._instance = Redis(connection_pool=cls._pool)
        return cls._instance
    
    @classmethod
    async def close(cls):
        """Close Redis connection"""
        if cls._instance:
            await cls._instance.close()
            await cls._pool.disconnect()
            cls._instance = None
            cls._pool = None


# Dependency to get Redis
async def get_redis() -> Redis:
    return await RedisClient.get_instance()
