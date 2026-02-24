import asyncio
import redis.asyncio as aioredis
from app.utils.circuit_breaker import RedisCircuitBreaker, CBState

async def test_distributed_redis_breaker():
    print("Connecting to Redis...")
    redis = aioredis.Redis.from_url("redis://localhost:6379/0", decode_responses=True)
    
    # Test 1: Instantiation
    breaker = RedisCircuitBreaker(redis, domain="database_check", failure_threshold=2, recovery_timeout_sec=2)
    
    # Reset State explicitly
    await redis.flushdb()
    
    print("Testing initial closed state...")
    assert await breaker.can_execute() is True
    
    print("Recording failures to breach threshold (Threshold: 2)...")
    await breaker.record_failure()
    assert await breaker.can_execute() is True
    
    await breaker.record_failure()
    
    print("Testing OPEN state...")
    assert await breaker.can_execute() is False
    
    state = await redis.get(breaker.k_state)
    print(f"Redis State is: {state}")
    
    print("Waiting 3 seconds for recovery timeout...")
    await asyncio.sleep(3)
    
    print("Testing HALF-OPEN state recovery...")
    assert await breaker.can_execute() is True
    
    print("Recording Success...")
    await breaker.record_success()
    
    state = await redis.get(breaker.k_state)
    print(f"Redis State returned to: {state}")
    
    print("All Circuit Breaker tests passed.")
    await redis.aclose()

if __name__ == "__main__":
    asyncio.run(test_distributed_redis_breaker())
