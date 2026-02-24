import redis.asyncio as aioredis
from typing import AsyncGenerator

async def init_redis_pool(url: str) -> AsyncGenerator[aioredis.Redis, None]:
    """Provides a managed connection pool for Redis clients."""
    pool = aioredis.ConnectionPool.from_url(
        url, decode_responses=True, max_connections=10
    )
    client = aioredis.Redis(connection_pool=pool)
    try:
        yield client
    finally:
        await client.aclose()
        await pool.disconnect()
